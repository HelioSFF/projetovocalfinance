import uuid
from datetime import datetime, timezone

from app.core.errors import AppError
from app.main import app
from app.models.financial_record import FinancialRecord
from app.routers.voice_records import get_voice_record_service
from tests.support.factories import record_kwargs
from tests.support.fakes import FakeVoiceRecordService


def build_record(**overrides):
    data = record_kwargs(**overrides)
    data["id"] = uuid.uuid4()
    return FinancialRecord(**data)


async def test_post_without_file_returns_400(client):
    response = await client.post("/api/voice-records")
    assert response.status_code == 400
    assert response.json() == {"error": {"code": "AUDIO_MISSING", "message": "Nenhum áudio recebido."}}


async def test_post_unsupported_mime_returns_415(client):
    fake = FakeVoiceRecordService(record=build_record())
    app.dependency_overrides[get_voice_record_service] = lambda: fake
    try:
        response = await client.post(
            "/api/voice-records",
            files={"file": ("notes.txt", b"hello", "text/plain")},
        )
    finally:
        app.dependency_overrides.pop(get_voice_record_service, None)
    assert response.status_code == 415
    assert response.json()["error"]["code"] == "AUDIO_UNSUPPORTED"
    assert fake.calls == 0


async def test_post_too_large_returns_413(client):
    fake = FakeVoiceRecordService(record=build_record())
    app.dependency_overrides[get_voice_record_service] = lambda: fake
    try:
        response = await client.post(
            "/api/voice-records",
            files={"file": ("audio.mp3", b"x" * (11 * 1024 * 1024), "audio/mpeg")},
        )
    finally:
        app.dependency_overrides.pop(get_voice_record_service, None)
    assert response.status_code == 413
    assert response.json()["error"]["code"] == "AUDIO_TOO_LARGE"
    assert fake.calls == 0


async def test_post_maps_service_error_to_status_and_format(client):
    fake = FakeVoiceRecordService(error=AppError("NOT_FINANCIAL", "Isso não parece um gasto ou ganho. Tente de novo.", 422))
    app.dependency_overrides[get_voice_record_service] = lambda: fake
    try:
        response = await client.post(
            "/api/voice-records",
            files={"file": ("audio.m4a", b"fake-audio", "audio/m4a")},
        )
    finally:
        app.dependency_overrides.pop(get_voice_record_service, None)
    assert response.status_code == 422
    assert response.json() == {"error": {"code": "NOT_FINANCIAL", "message": "Isso não parece um gasto ou ganho. Tente de novo."}}


async def test_post_returns_201_with_record(client):
    record = build_record(item="cafe-teste")
    fake = FakeVoiceRecordService(record=record)
    app.dependency_overrides[get_voice_record_service] = lambda: fake
    try:
        response = await client.post(
            "/api/voice-records",
            files={"file": ("audio.m4a", b"fake-audio", "audio/m4a")},
        )
    finally:
        app.dependency_overrides.pop(get_voice_record_service, None)
    assert response.status_code == 201
    payload = response.json()
    assert payload["item"] == "cafe-teste"
    assert payload["quantity"] == "3"
    assert payload["unit_price"] == "5.00"
    assert payload["total"] == "15.00"
    assert payload["category_label"] == "Alimentação"
