from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.clients.deepseek_client import build_deepseek_client
from app.clients.openai_client import build_openai_client
from app.core.config import Settings, settings
from app.core.errors import AppError
from app.db.session import get_session
from app.schemas.financial_record import FinancialRecordOut
from app.services.decision_service import DecisionService
from app.services.extraction_service import ExtractionService
from app.services.pipeline_trace import NullTrace, PipelineTrace
from app.services.rewrite_service import RewriteService
from app.services.transcription_service import TranscriptionService
from app.services.voice_record_service import VoiceRecordService

router = APIRouter(prefix="/api")

ACCEPTED_MIME_TYPES = {
    "audio/m4a",
    "audio/x-m4a",
    "audio/mp4",
    "audio/aac",
    "audio/webm",
    "video/webm",
    "audio/mpeg",
    "audio/wav",
    "audio/ogg",
}

EXTENSION_BY_MIME = {
    "audio/m4a": "m4a",
    "audio/x-m4a": "m4a",
    "audio/mp4": "mp4",
    "audio/aac": "aac",
    "audio/webm": "webm",
    "video/webm": "webm",
    "audio/mpeg": "mp3",
    "audio/wav": "wav",
    "audio/ogg": "ogg",
}


def parse_client_duration(value: str | None) -> int | None:
    try:
        parsed = int(value) if value is not None else None
    except (TypeError, ValueError):
        return None
    if parsed is None or not 0 <= parsed <= 120000:
        return None
    return parsed


def get_trace(duration_ms: str | None = Form(default=None)) -> NullTrace:
    if not settings.dev_tools_enabled():
        return NullTrace()
    return PipelineTrace(settings.decision_threshold, parse_client_duration(duration_ms))


def build_voice_record_service(
    session: AsyncSession,
    app_settings: Settings,
    openai_client,
    deepseek_client,
    trace: NullTrace = NullTrace(),
) -> VoiceRecordService:
    return VoiceRecordService(
        transcription=TranscriptionService(openai_client, app_settings.ai_timeout_seconds, trace),
        decision=DecisionService(openai_client, app_settings.ai_timeout_seconds, trace),
        extraction=ExtractionService(
            openai_client,
            app_settings.extraction_model,
            app_settings.openai_service_tier,
            app_settings.ai_timeout_seconds,
            trace,
        ),
        rewrite=RewriteService(deepseek_client, app_settings.ai_timeout_seconds, trace),
        threshold=app_settings.decision_threshold,
        trace=trace,
    )


def get_voice_record_service(
    request: Request, trace: NullTrace = Depends(get_trace), session: AsyncSession = Depends(get_session)
) -> VoiceRecordService:
    openai_client = getattr(request.app.state, "openai_client", None) or build_openai_client(settings)
    deepseek_client = getattr(request.app.state, "deepseek_client", None) or build_deepseek_client(settings)
    return build_voice_record_service(session, settings, openai_client, deepseek_client, trace)


@router.post("/voice-records", response_model=FinancialRecordOut, status_code=201)
async def create_voice_record(
    file: UploadFile | None = File(default=None),
    service: VoiceRecordService = Depends(get_voice_record_service),
    trace: NullTrace = Depends(get_trace),
    session: AsyncSession = Depends(get_session),
):
    with trace.stage("validate"):
        if file is None:
            raise AppError("AUDIO_MISSING", "Nenhum áudio recebido.", 400)
        mime = (file.content_type or "").split(";")[0].strip().lower()
        if mime not in ACCEPTED_MIME_TYPES:
            raise AppError("AUDIO_UNSUPPORTED", "Formato de áudio não suportado.", 415)
        audio = await file.read()
        if len(audio) > settings.max_audio_mb * 1024 * 1024:
            raise AppError("AUDIO_TOO_LARGE", "Áudio muito longo.", 413)
    filename = f"audio.{EXTENSION_BY_MIME[mime]}"
    record = await service.register(audio, filename, mime, session)
    body = FinancialRecordOut.from_orm_with_label(record).model_dump(mode="json")
    if trace.enabled:
        body["debug"] = trace.to_dict()
    return JSONResponse(status_code=201, content=body)
