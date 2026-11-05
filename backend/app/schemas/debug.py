import json

from app.schemas.ai import DecisionResult, ExtractionResult
from app.services.record_rules import failure_code


def _get(entry, key, default=None):
    if isinstance(entry, dict):
        return entry.get(key, default)
    return getattr(entry, key, default)


def summarize_decision_answers(answers) -> list[dict]:
    summarized = []
    for answer in answers or []:
        name = _get(answer, "name")
        kind = _get(answer, "type")
        if kind == "refusal":
            summarized.append(
                {
                    "name": name,
                    "type": "refusal",
                    "probability": None,
                    "choice": None,
                    "confidence": None,
                    "top_probabilities": [],
                    "refusal": _get(answer, "message", _get(answer, "text")),
                }
            )
            continue
        probabilities = _get(answer, "probabilities", []) or []
        ranked = sorted(probabilities, key=lambda entry: _get(entry, "probability", 0) or 0, reverse=True)[:3]
        summarized.append(
            {
                "name": name,
                "type": kind,
                "probability": _get(answer, "probability"),
                "choice": _get(answer, "choice"),
                "confidence": _get(answer, "confidence"),
                "top_probabilities": [
                    {"value": _get(entry, "value"), "probability": _get(entry, "probability")} for entry in ranked
                ],
                "refusal": None,
            }
        )
    return summarized


def _usage_details(usage):
    details = _get(usage, "input_tokens_details")
    if details is None:
        details = _get(usage, "input_token_details")
    return details


def summarize_decision_usage(response) -> dict:
    usage = getattr(response, "usage", None)
    details = _usage_details(usage) if usage is not None else None
    return {
        "input_tokens": _get(usage, "input_tokens", 0) or 0,
        "cached_tokens": _get(details, "cached_tokens", 0) or 0,
        "cache_write_tokens": _get(details, "cache_write_tokens", _get(details, "cache_write", 0)) or 0,
        "output_tokens": _get(usage, "output_tokens", 0) or 0,
    }


def summarize_extraction_usage(response) -> dict:
    usage = getattr(response, "usage", None)
    details = _usage_details(usage) if usage is not None else None
    output_details = _get(usage, "output_tokens_details") if usage is not None else None
    return {
        "input_tokens": _get(usage, "input_tokens", 0) or 0,
        "cached_tokens": _get(details, "cached_tokens", 0) or 0,
        "output_tokens": _get(usage, "output_tokens", 0) or 0,
        "reasoning_tokens": _get(output_details, "reasoning_tokens", 0) or 0,
    }


def summarize_fallback_usage(response) -> dict | None:
    usage = getattr(response, "usage", None)
    if usage is None:
        return None
    return {
        "prompt_tokens": _get(usage, "prompt_tokens"),
        "completion_tokens": _get(usage, "completion_tokens"),
        "prompt_cache_hit_tokens": _get(usage, "prompt_cache_hit_tokens"),
        "prompt_cache_miss_tokens": _get(usage, "prompt_cache_miss_tokens"),
    }


def raw_output_text(response) -> str | None:
    try:
        for item in response.output:
            if getattr(item, "type", None) != "message":
                continue
            for part in item.content:
                if getattr(part, "type", None) not in ("output_text", "text"):
                    continue
                return part.text
    except (AttributeError, TypeError):
        return None
    return None


def extraction_to_dict(result: ExtractionResult | None) -> dict | None:
    if result is None:
        return None
    return {
        "item": result.item,
        "quantity": result.quantity,
        "unit_price": result.unit_price,
        "stated_total": result.stated_total,
    }


def acceptance_summary(decision: DecisionResult, extraction: ExtractionResult | None, threshold: float) -> dict:
    plausible_value = decision.plausible
    financial_value = decision.is_financial
    plausible = {"value": plausible_value, "passed": plausible_value is not None and plausible_value >= threshold}
    is_financial = {"value": financial_value, "passed": financial_value is not None and financial_value >= threshold}
    extraction_valid = (
        extraction is not None
        and bool(extraction.item and extraction.item.strip())
        and extraction.quantity is not None
        and extraction.quantity > 0
        and ((extraction.unit_price or 0) > 0 or (extraction.stated_total or 0) > 0)
    )
    accepted = plausible["passed"] and is_financial["passed"] and extraction_valid
    return {
        "plausible": plausible,
        "is_financial": is_financial,
        "extraction_valid": extraction_valid,
        "accepted": accepted,
        "failure_code": None if accepted else failure_code(decision, threshold),
    }


def parse_extraction_text(raw_text: str | None):
    if not raw_text:
        return None
    try:
        return json.loads(raw_text)
    except ValueError:
        return None
