import logging
import time
from contextlib import contextmanager
from decimal import Decimal

from app.core import pricing
from app.schemas import debug as debug_schemas
from app.schemas.ai import DecisionResult, ExtractionResult
from app.schemas.financial_record import format_money, format_quantity
from app.services import cost_calculator
from app.services.record_rules import failure_code, is_accepted

logger = logging.getLogger(__name__)

STAGE_LABELS = {
    "validate": "Validação do áudio",
    "transcribe": "Transcrição",
    "analyze": "Análise (paralela)",
    "decision": "Decisions",
    "extraction": "Extração",
    "rewrite": "Reescrita",
    "rules": "Cálculo e reconciliação",
    "db_insert": "Gravação no banco",
}


class NullTrace:
    enabled = False

    @contextmanager
    def stage(self, name: str, attempt: int | None = None, parallel: bool = False):
        yield None

    def start_attempt(self, number: int, source: str, input_text: str) -> None:
        return None

    def set_transcription(self, model: str, text: str, response) -> None:
        return None

    def set_decision(self, attempt: int, model: str, response) -> None:
        return None

    def set_extraction(
        self, attempt: int, model: str, service_tier: str | None, response, raw_text: str | None, parsed: dict | None
    ) -> None:
        return None

    def set_acceptance(self, attempt: int, decision: DecisionResult, extraction: ExtractionResult | None, threshold: float) -> None:
        return None

    def set_fallback(self, model: str, input_text: str, response, rewritten_text: str) -> None:
        return None

    def set_result(self, decision: DecisionResult, record, total_source: str) -> None:
        return None

    def fail(self, code: str) -> None:
        return None

    def to_dict(self) -> dict | None:
        return None


class PipelineTrace(NullTrace):
    enabled = True

    def __init__(self, threshold: float, client_duration_ms: int | None = None):
        self.threshold = threshold
        self.t0 = time.perf_counter()
        self.stages: list[dict] = []
        self.attempts: list[dict] = []
        self.transcription: dict | None = None
        self.transcribe_seconds: float | None = None
        self.transcribe_estimated: bool = True
        self.fallback: dict = {
            "used": False,
            "model": None,
            "input_text": None,
            "rewritten_text": None,
            "usage": None,
        }
        self.result: dict | None = None
        self.failure_code: str | None = None
        self.client_seconds = client_duration_ms / 1000 if client_duration_ms is not None else None

    def _elapsed_ms(self) -> int:
        return int(round((time.perf_counter() - self.t0) * 1000))

    @contextmanager
    def stage(self, name: str, attempt: int | None = None, parallel: bool = False):
        entry: dict = {
            "name": name,
            "label": STAGE_LABELS[name],
            "attempt": attempt,
            "started_ms": self._elapsed_ms(),
            "duration_ms": 0,
            "parallel": parallel,
        }
        self.stages.append(entry)
        try:
            yield entry
        except Exception as exc:
            entry["error"] = type(exc).__name__
            status = getattr(exc, "status_code", None)
            if isinstance(status, int):
                entry["http_status"] = status
            raise
        finally:
            entry["duration_ms"] = self._elapsed_ms() - entry["started_ms"]

    def _attempt(self, number: int) -> dict:
        for attempt in self.attempts:
            if attempt["number"] == number:
                return attempt
        raise KeyError(f"attempt {number} not started")

    def start_attempt(self, number: int, source: str, input_text: str) -> None:
        self.attempts.append(
            {
                "number": number,
                "source": source,
                "input_text": input_text,
                "decision": None,
                "extraction": None,
                "acceptance": None,
            }
        )

    def set_transcription(self, model: str, text: str, response) -> None:
        usage = getattr(response, "usage", None)
        seconds = getattr(usage, "seconds", None) if usage is not None else None
        usage_type = getattr(usage, "type", None) if usage is not None else None
        if usage_type == "duration" and isinstance(seconds, (int, float)):
            source = "provider"
            audio_seconds: float | None = float(seconds)
            estimated = False
            usage_summary: dict | None = {"type": "duration", "seconds": audio_seconds}
        elif self.client_seconds is not None:
            source = "client"
            audio_seconds = self.client_seconds
            estimated = True
            usage_summary = {"type": "client", "seconds": audio_seconds}
        else:
            source = None
            audio_seconds = None
            estimated = True
            usage_summary = None
        self.transcribe_seconds = audio_seconds
        self.transcribe_estimated = estimated
        self.transcription = {
            "model": model,
            "text": text,
            "audio_seconds": audio_seconds,
            "audio_seconds_source": source,
            "usage": usage_summary,
        }

    def set_decision(self, attempt: int, model: str, response) -> None:
        self._attempt(attempt)["decision"] = {
            "model": model,
            "answers": debug_schemas.summarize_decision_answers(getattr(response, "answers", [])),
            "usage": debug_schemas.summarize_decision_usage(response),
        }

    def set_extraction(
        self, attempt: int, model: str, service_tier: str | None, response, raw_text: str | None, parsed: dict | None
    ) -> None:
        self._attempt(attempt)["extraction"] = {
            "model": model,
            "service_tier": service_tier,
            "raw_text": raw_text,
            "parsed": parsed,
            "usage": debug_schemas.summarize_extraction_usage(response),
        }

    def set_acceptance(self, attempt: int, decision: DecisionResult, extraction: ExtractionResult | None, threshold: float) -> None:
        self._attempt(attempt)["acceptance"] = debug_schemas.acceptance_summary(decision, extraction, threshold)

    def set_fallback(self, model: str, input_text: str, response, rewritten_text: str) -> None:
        self.fallback = {
            "used": True,
            "model": model,
            "input_text": input_text,
            "rewritten_text": rewritten_text,
            "usage": debug_schemas.summarize_fallback_usage(response),
        }

    def set_result(self, decision: DecisionResult, record, total_source: str) -> None:
        quantity = format_quantity(record.quantity)
        unit_price = format_money(record.unit_price)
        total = format_money(record.total)
        self.result = {
            "type_choice": decision.record_type,
            "category_choice": decision.category,
            "type": record.type,
            "category": record.category,
            "reconciled": decision.record_type != record.type or decision.category != record.category,
            "quantity": quantity,
            "unit_price": unit_price,
            "total": total,
            "total_source": total_source,
            "formula": f"{quantity} × {unit_price} = {total}",
        }

    def fail(self, code: str) -> None:
        self.failure_code = code

    def outcome(self) -> str:
        if self.result is not None:
            return "accepted"
        if self.failure_code == "AI_UNAVAILABLE":
            return "provider_error"
        if self.failure_code == "DB_UNAVAILABLE":
            return "db_error"
        return "rejected"

    def _decision_cost_line(self, attempt: dict) -> dict:
        usage = attempt["decision"]["usage"]
        price = pricing.PRICES[pricing.DECISIONS_LUNA]
        cost = cost_calculator.token_cost(
            price, usage["input_tokens"], usage["cached_tokens"], usage["cache_write_tokens"], usage["output_tokens"]
        )
        return {
            "stage": "decision",
            "attempt": attempt["number"],
            "model": attempt["decision"]["model"],
            "basis": f"{usage['input_tokens']} in, {usage['cached_tokens']} cached, {usage['cache_write_tokens']} write",
            "usd": cost_calculator.format_usd(cost),
            "estimated": price.estimated,
        }

    def _extraction_cost_line(self, attempt: dict) -> dict:
        extraction = attempt["extraction"]
        usage = extraction["usage"]
        model = extraction["model"]
        key = {"gpt-6-luna": pricing.RESPONSES_LUNA, "gpt-4o-mini": pricing.RESPONSES_MINI}.get(model)
        price = pricing.PRICES.get(key) if key is not None else None
        multiplier = pricing.PRIORITY_MULTIPLIER if extraction["service_tier"] else Decimal(1)
        if price is None:
            return {
                "stage": "extraction",
                "attempt": attempt["number"],
                "model": model,
                "basis": f"{usage['input_tokens']} in, {usage['cached_tokens']} cached, {usage['output_tokens']} out",
                "usd": None,
                "estimated": True,
            }
        cost = cost_calculator.token_cost(
            price,
            usage["input_tokens"],
            usage["cached_tokens"],
            0,
            usage["output_tokens"],
            multiplier=multiplier,
        )
        return {
            "stage": "extraction",
            "attempt": attempt["number"],
            "model": model,
            "basis": f"{usage['input_tokens']} in, {usage['cached_tokens']} cached, {usage['output_tokens']} out",
            "usd": cost_calculator.format_usd(cost),
            "estimated": price.estimated or bool(extraction["service_tier"]),
        }

    def _fallback_cost_line(self) -> dict | None:
        if not self.fallback["used"]:
            return None
        usage = self.fallback["usage"] or {}
        prompt_tokens = usage.get("prompt_cache_miss_tokens")
        if prompt_tokens is None:
            prompt_tokens = usage.get("prompt_tokens", 0) or 0
        cached_tokens = usage.get("prompt_cache_hit_tokens", 0) or 0
        completion_tokens = usage.get("completion_tokens", 0) or 0
        price = pricing.PRICES[pricing.CHAT_DEEPSEEK_FLASH]
        cost = cost_calculator.token_cost(price, prompt_tokens, cached_tokens, 0, completion_tokens)
        return {
            "stage": "rewrite",
            "attempt": None,
            "model": self.fallback["model"],
            "basis": f"{prompt_tokens} prompt, {completion_tokens} completion",
            "usd": cost_calculator.format_usd(cost),
            "estimated": True,
        }

    def _transcribe_cost_line(self) -> dict | None:
        if self.transcription is None:
            return None
        cost = cost_calculator.transcribe_cost(self.transcribe_seconds)
        if cost is None:
            return {
                "stage": "transcribe",
                "attempt": None,
                "model": self.transcription["model"],
                "basis": "duration unknown",
                "usd": None,
                "estimated": True,
            }
        seconds = self.transcribe_seconds or 0
        return {
            "stage": "transcribe",
            "attempt": None,
            "model": self.transcription["model"],
            "basis": f"{seconds} s × 0.0045/min",
            "usd": cost_calculator.format_usd(cost),
            "estimated": self.transcribe_estimated,
        }

    def _costs(self) -> dict:
        lines = []
        transcribe_line = self._transcribe_cost_line()
        if transcribe_line is not None:
            lines.append(transcribe_line)
        for attempt in self.attempts:
            if attempt["decision"] is not None:
                lines.append(self._decision_cost_line(attempt))
            if attempt["extraction"] is not None:
                lines.append(self._extraction_cost_line(attempt))
        fallback_line = self._fallback_cost_line()
        if fallback_line is not None:
            lines.append(fallback_line)
        total = sum((Decimal(line["usd"]) for line in lines if line["usd"] is not None), Decimal(0))
        return {
            "currency": "USD",
            "lines": lines,
            "total_usd": cost_calculator.format_usd(total),
            "estimated": any(line["estimated"] for line in lines),
        }

    def to_dict(self) -> dict | None:
        outcome = self.outcome()
        costs = self._costs()
        payload = {
            "version": 1,
            "app_env": "development",
            "outcome": outcome,
            "failure_code": None if outcome == "accepted" else self.failure_code,
            "threshold": self.threshold,
            "timing": {
                "server_total_ms": self._elapsed_ms(),
                "stages": self.stages,
            },
            "transcription": self.transcription,
            "attempts": self.attempts,
            "fallback": self.fallback,
            "costs": costs,
            "result": self.result,
        }
        for entry in self.stages:
            logger.info(
                "devtools stage=%s attempt=%s duration_ms=%d parallel=%s",
                entry["name"],
                entry["attempt"],
                entry["duration_ms"],
                entry["parallel"],
            )
        for line in costs["lines"]:
            logger.info(
                "devtools cost stage=%s attempt=%s model=%s basis=%s usd=%s",
                line["stage"],
                line["attempt"],
                line["model"],
                line["basis"],
                line["usd"],
            )
        logger.info("devtools total_usd=%s estimated=%s", costs["total_usd"], costs["estimated"])
        return payload
