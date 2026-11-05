import asyncio

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError, ProviderError
from app.models.financial_record import FinancialRecord
from app.repositories.financial_record_repository import FinancialRecordRepository
from app.schemas.ai import DecisionResult, ExtractionResult
from app.services.decision_service import DecisionService
from app.services.extraction_service import ExtractionService
from app.services.pipeline_trace import NullTrace
from app.services.record_rules import compute_amounts, failure_code, is_accepted, reconcile_type_category, resolve_prices
from app.services.rewrite_service import RewriteService
from app.services.transcription_service import TranscriptionService

MESSAGES = {
    "NOT_UNDERSTOOD": "Não entendi o gasto. Tente de novo, por exemplo: comprei 2 cafés de 5 reais.",
    "NOT_FINANCIAL": "Isso não parece um gasto ou ganho. Tente de novo.",
}


class VoiceRecordService:
    def __init__(
        self,
        transcription: TranscriptionService,
        decision: DecisionService,
        extraction: ExtractionService,
        rewrite: RewriteService,
        threshold: float,
        trace: NullTrace = NullTrace(),
    ):
        self.transcription = transcription
        self.decision = decision
        self.extraction = extraction
        self.rewrite = rewrite
        self.threshold = threshold
        self.trace = trace

    async def register(self, audio: bytes, filename: str, mime: str, session: AsyncSession) -> FinancialRecord:
        with self.trace.stage("transcribe"):
            try:
                transcript = await self.transcription.transcribe(audio, filename, mime)
            except ProviderError:
                raise self.provider_error()
            except Exception as exc:
                raise self.provider_error() from exc
        if not transcript:
            raise self.fail_with("NOT_UNDERSTOOD")
        self.trace.start_attempt(1, "transcript", transcript)
        decision, extraction = await self.analyze(transcript, attempt=1)
        self.trace.set_acceptance(1, decision, extraction, self.threshold)
        normalized_text = None
        if not is_accepted(decision, extraction, self.threshold):
            with self.trace.stage("rewrite"):
                try:
                    rewritten = await self.rewrite.rewrite(transcript)
                except ProviderError:
                    raise self.provider_error()
                except Exception as exc:
                    raise self.provider_error() from exc
            if not rewritten:
                raise self.decision_error(decision)
            normalized_text = rewritten
            self.trace.start_attempt(2, "rewrite", rewritten)
            decision, extraction = await self.analyze(normalized_text, attempt=2)
            self.trace.set_acceptance(2, decision, extraction, self.threshold)
            if not is_accepted(decision, extraction, self.threshold):
                raise self.decision_error(decision)
        return await self.build_record(decision, extraction, transcript, normalized_text, session)

    async def timed(self, name: str, attempt: int, coro):
        with self.trace.stage(name, attempt=attempt, parallel=True):
            return await coro

    async def analyze(self, text: str, attempt: int = 1) -> tuple[DecisionResult, ExtractionResult | None]:
        with self.trace.stage("analyze", attempt=attempt):
            try:
                decision, extraction = await asyncio.gather(
                    self.timed("decision", attempt, self.decision.decide(text, attempt)),
                    self.timed("extraction", attempt, self.extraction.extract(text, attempt)),
                )
            except ProviderError:
                raise self.provider_error()
            except Exception as exc:
                raise self.provider_error() from exc
        return decision, extraction

    def fail_with(self, code: str) -> AppError:
        self.trace.fail(code)
        error = AppError(code, MESSAGES[code], 422)
        error.debug = self.trace.to_dict()
        return error

    def provider_error(self) -> ProviderError:
        self.trace.fail("AI_UNAVAILABLE")
        error = ProviderError()
        error.debug = self.trace.to_dict()
        return error

    def decision_error(self, decision: DecisionResult) -> AppError:
        return self.fail_with(failure_code(decision, self.threshold))

    async def build_record(
        self,
        decision: DecisionResult,
        extraction: ExtractionResult | None,
        transcript: str,
        normalized_text: str | None,
        session: AsyncSession,
    ) -> FinancialRecord:
        assert extraction is not None
        with self.trace.stage("rules"):
            try:
                unit_price, stated_total = resolve_prices(
                    transcript, extraction.quantity, extraction.unit_price, extraction.stated_total
                )
                quantity, unit_price, total = compute_amounts(extraction.quantity or 0, unit_price, stated_total)
            except ValueError as exc:
                raise self.fail_with("NOT_UNDERSTOOD") from exc
            record_type, category = reconcile_type_category(decision.record_type, decision.category)
        total_source = "unit_price" if unit_price is not None else "stated_total"
        repository = FinancialRecordRepository(session)
        with self.trace.stage("db_insert"):
            try:
                record = await repository.create(
                    record_type=record_type,
                    category=category,
                    item=extraction.item.strip(),
                    quantity=quantity,
                    unit_price=unit_price,
                    total=total,
                    transcript=transcript,
                    normalized_text=normalized_text,
                )
            except Exception as exc:
                self.trace.fail("DB_UNAVAILABLE")
                error = AppError("DB_UNAVAILABLE", "Banco de dados indisponível.", 503)
                error.debug = self.trace.to_dict()
                raise error from exc
        self.trace.set_result(decision, record, total_source)
        return record
