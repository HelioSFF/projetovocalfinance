from app.core.errors import AppError
from app.main import app
from app.models.financial_record import FinancialRecord
from app.routers.voice_records import build_voice_record_service, get_trace, get_voice_record_service
from app.services.pipeline_trace import PipelineTrace
from app.core.config import settings
from tests.support.fakes import (
    FakeOpenAIClient,
    FakeVoiceRecordService,
    decision_response_ns,
    extraction_response_ns,
    rewrite_response_ns,
    standard_answers_ns,
    transcription_result_ns,
)
from tests.support.factories import record_kwargs

import uuid


def make_service(db_session, trace, openai_fake, deepseek_fake):
    return build_voice_record_service(db_session, settings, openai_fake, deepseek_fake, trace)


def program_accept(openai_fake, transcript="Comprei três cafés de cinco reais.", seconds=4.0):
    openai_fake.audio.transcriptions.create.return_value = transcription_result_ns(transcript, seconds)
    openai_fake.decisions.create.return_value = decision_response_ns(standard_answers_ns())
    openai_fake.responses.create.return_value = extraction_response_ns(
        {"item": "café", "quantity": 3, "unit_price": 5, "stated_total": 15}
    )


def program_refusal(openai_fake, transcript="bla"):
    openai_fake.audio.transcriptions.create.return_value = transcription_result_ns(transcript, 3.0)
    answers = standard_answers_ns(financial=0.1)
    openai_fake.decisions.create.return_value = decision_response_ns(answers)
    openai_fake.responses.create.return_value = extraction_response_ns(
        {"item": "bla", "quantity": 1, "unit_price": 2, "stated_total": 2}
    )


def override_dev(client, db_session, monkeypatch, trace, service):
    monkeypatch.setattr(settings, "app_env", "development")
    app.dependency_overrides[get_trace] = lambda: trace
    app.dependency_overrides[get_voice_record_service] = lambda: service


def clear_voice_overrides():
    app.dependency_overrides.pop(get_trace, None)
    app.dependency_overrides.pop(get_voice_record_service, None)


async def test_dev_accept_201_with_full_debug(client, db_session, monkeypatch):
    trace = PipelineTrace(0.6, None)
    openai_fake = FakeOpenAIClient()
    deepseek_fake = FakeOpenAIClient()
    program_accept(openai_fake)
    service = make_service(db_session, trace, openai_fake, deepseek_fake)
    override_dev(client, db_session, monkeypatch, trace, service)
    try:
        response = await client.post("/api/voice-records", files={"file": ("audio.m4a", b"fake-audio", "audio/m4a")})
    finally:
        clear_voice_overrides()
    assert response.status_code == 201
    body = response.json()
    assert body["total"] == "15.00"
    debug = body["debug"]
    assert debug["version"] == 1
    assert debug["app_env"] == "development"
    assert debug["outcome"] == "accepted"
    assert debug["failure_code"] is None
    assert debug["threshold"] == 0.6
    assert [stage["name"] for stage in debug["timing"]["stages"]] == [
        "validate",
        "transcribe",
        "analyze",
        "decision",
        "extraction",
        "rules",
        "db_insert",
    ]
    assert debug["transcription"]["model"] == "gpt-transcribe"
    assert debug["transcription"]["text"] == "Comprei três cafés de cinco reais."
    assert len(debug["attempts"]) == 1
    assert len(debug["attempts"][0]["decision"]["answers"]) == 4
    assert debug["attempts"][0]["extraction"]["parsed"]["item"] == "café"
    assert debug["fallback"]["used"] is False
    assert debug["result"]["total"] == body["total"]
    assert debug["costs"]["total_usd"] is not None


async def test_dev_refusal_422_with_two_attempts(client, db_session, monkeypatch):
    trace = PipelineTrace(0.6, None)
    openai_fake = FakeOpenAIClient()
    deepseek_fake = FakeOpenAIClient()
    deepseek_fake.chat.completions.create.return_value = rewrite_response_ns("bla reescrito")
    program_refusal(openai_fake)
    service = make_service(db_session, trace, openai_fake, deepseek_fake)
    override_dev(client, db_session, monkeypatch, trace, service)
    try:
        response = await client.post("/api/voice-records", files={"file": ("audio.m4a", b"fake-audio", "audio/m4a")})
    finally:
        clear_voice_overrides()
    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "NOT_FINANCIAL"
    assert body["debug"]["outcome"] == "rejected"
    assert len(body["debug"]["attempts"]) == 2
    assert body["debug"]["fallback"]["used"] is True


async def test_dev_provider_failure_503_with_debug(client, db_session, monkeypatch):
    trace = PipelineTrace(0.6, None)
    openai_fake = FakeOpenAIClient()
    openai_fake.audio.transcriptions.create.side_effect = TimeoutError("timed out")
    deepseek_fake = FakeOpenAIClient()
    service = make_service(db_session, trace, openai_fake, deepseek_fake)
    override_dev(client, db_session, monkeypatch, trace, service)
    try:
        response = await client.post("/api/voice-records", files={"file": ("audio.m4a", b"fake-audio", "audio/m4a")})
    finally:
        clear_voice_overrides()
    assert response.status_code == 503
    body = response.json()
    assert body["error"]["code"] == "AI_UNAVAILABLE"
    assert body["debug"]["outcome"] == "provider_error"
    assert any(stage.get("error") for stage in body["debug"]["timing"]["stages"])


async def test_prod_accept_201_without_debug_key(client, db_session, monkeypatch):
    monkeypatch.setattr(settings, "app_env", "production")
    data = record_kwargs(item="sem-debug")
    data["id"] = uuid.uuid4()
    fake = FakeVoiceRecordService(record=FinancialRecord(**data))
    app.dependency_overrides[get_voice_record_service] = lambda: fake
    try:
        response = await client.post("/api/voice-records", files={"file": ("audio.m4a", b"fake-audio", "audio/m4a")})
    finally:
        app.dependency_overrides.pop(get_voice_record_service, None)
    assert response.status_code == 201
    body = response.json()
    assert "debug" not in body
    assert set(body.keys()) == {
        "id",
        "type",
        "category",
        "category_label",
        "item",
        "quantity",
        "unit_price",
        "total",
        "currency",
        "transcript",
        "normalized_text",
        "created_at",
    }


async def test_prod_error_without_debug_key(client, db_session, monkeypatch):
    monkeypatch.setattr(settings, "app_env", "production")
    fake = FakeVoiceRecordService(error=AppError("NOT_FINANCIAL", "Isso não parece um gasto ou ganho. Tente de novo.", 422))
    app.dependency_overrides[get_voice_record_service] = lambda: fake
    try:
        response = await client.post("/api/voice-records", files={"file": ("audio.m4a", b"fake-audio", "audio/m4a")})
    finally:
        app.dependency_overrides.pop(get_voice_record_service, None)
    assert response.status_code == 422
    assert "debug" not in response.json()


async def test_security_no_secrets_leak(client, db_session, monkeypatch):
    monkeypatch.setattr(settings, "app_env", "development")
    monkeypatch.setattr(settings, "openai_api_key", "sk-test-SECRET")
    monkeypatch.setattr(settings, "deepseek_api_key", "ds-test-SECRET")
    trace = PipelineTrace(0.6, None)
    openai_fake = FakeOpenAIClient()
    openai_fake.audio.transcriptions.create.side_effect = Exception("401 invalid key sk-test-SECRET ...")
    deepseek_fake = FakeOpenAIClient()
    service = make_service(db_session, trace, openai_fake, deepseek_fake)
    override_dev(client, db_session, monkeypatch, trace, service)
    try:
        response = await client.post("/api/voice-records", files={"file": ("audio.m4a", b"fake-audio", "audio/m4a")})
    finally:
        clear_voice_overrides()
    assert response.status_code == 503
    raw = response.text
    assert "sk-test-SECRET" not in raw
    assert "ds-test-SECRET" not in raw
    assert "Bearer" not in raw
    assert "Authorization" not in raw


async def test_invalid_duration_ms_ignored(client, db_session, monkeypatch):
    monkeypatch.setattr(settings, "app_env", "development")
    trace = PipelineTrace(0.6, None)
    openai_fake = FakeOpenAIClient()
    deepseek_fake = FakeOpenAIClient()
    program_accept(openai_fake)
    service = make_service(db_session, trace, openai_fake, deepseek_fake)
    override_dev(client, db_session, monkeypatch, trace, service)
    try:
        for invalid in ["abc", "-5", "999999"]:
            response = await client.post(
                "/api/voice-records",
                files={"file": ("audio.m4a", b"fake-audio", "audio/m4a")},
                data={"duration_ms": invalid},
            )
            assert response.status_code == 201
    finally:
        clear_voice_overrides()


async def test_dev_db_row_has_standard_columns_only(client, db_session, monkeypatch):
    trace = PipelineTrace(0.6, None)
    openai_fake = FakeOpenAIClient()
    deepseek_fake = FakeOpenAIClient()
    program_accept(openai_fake, transcript="Gastei 45 no mercado")
    service = make_service(db_session, trace, openai_fake, deepseek_fake)
    override_dev(client, db_session, monkeypatch, trace, service)
    try:
        response = await client.post("/api/voice-records", files={"file": ("audio.m4a", b"fake-audio", "audio/m4a")})
    finally:
        clear_voice_overrides()
    assert response.status_code == 201
    columns = [column.name for column in FinancialRecord.__table__.columns]
    assert columns == [
        "id",
        "type",
        "category",
        "item",
        "quantity",
        "unit_price",
        "total",
        "currency",
        "transcript",
        "normalized_text",
        "created_at",
    ]
