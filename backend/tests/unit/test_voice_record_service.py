import asyncio

import pytest

from app.core.errors import AppError
from app.services.voice_record_service import VoiceRecordService
from tests.support.fakes import (
    FakeDecision,
    FakeExtraction,
    FakeRewrite,
    FakeTranscription,
    bad_decision,
    good_decision,
    good_extraction,
    provider_error,
)
from tests.support.factories import unique_tag


def make_service(transcription, decision, extraction, rewrite):
    return VoiceRecordService(
        transcription=transcription,
        decision=decision,
        extraction=extraction,
        rewrite=rewrite,
        threshold=0.6,
    )


async def test_success_first_try_saves_without_normalized_text(db_session):
    tag = unique_tag()
    service = make_service(
        FakeTranscription(f"comprei cafe {tag}"),
        FakeDecision([good_decision()]),
        FakeExtraction([good_extraction(item=f"cafe-{tag}")]),
        FakeRewrite("reescrita"),
    )
    record = await service.register(b"audio", "audio.m4a", "audio/m4a", db_session)
    assert record.item == f"cafe-{tag}"
    assert record.normalized_text is None
    assert str(record.total) == "15.00"


async def test_rejection_then_rewrite_success_saves_normalized_text(db_session):
    tag = unique_tag()
    service = make_service(
        FakeTranscription(f"audio {tag}"),
        FakeDecision([bad_decision(), good_decision()]),
        FakeExtraction([good_extraction(), good_extraction(item=f"pao-{tag}")]),
        FakeRewrite(f"pao {tag} dois reais"),
    )
    record = await service.register(b"audio", "audio.m4a", "audio/m4a", db_session)
    assert record.normalized_text == f"pao {tag} dois reais"
    assert record.item == f"pao-{tag}"


async def test_double_rejection_raises_422_and_rewrites_once(db_session):
    rewrite = FakeRewrite("bla reescrito")
    service = make_service(
        FakeTranscription("bla"),
        FakeDecision([bad_decision(), bad_decision()]),
        FakeExtraction([good_extraction(), good_extraction()]),
        rewrite,
    )
    with pytest.raises(AppError) as exc_info:
        await service.register(b"audio", "audio.webm", "video/webm", db_session)
    assert exc_info.value.status == 422
    assert exc_info.value.code == "NOT_FINANCIAL"
    assert rewrite.calls == 1


async def test_slang_without_total_word_computes_unit_times_quantity(db_session):
    service = make_service(
        FakeTranscription("desci três de dez conto"),
        FakeDecision([good_decision(category="other_expense")]),
        FakeExtraction([good_extraction(item="não especificado", quantity=3, unit_price=None, stated_total=10.0)]),
        FakeRewrite("reescrita"),
    )
    record = await service.register(b"audio", "audio.webm", "video/webm", db_session)
    assert str(record.unit_price) == "10.00"
    assert str(record.total) == "30.00"


async def test_total_word_keeps_stated_total(db_session):
    service = make_service(
        FakeTranscription("gastei 100 em 3 cervejas"),
        FakeDecision([good_decision()]),
        FakeExtraction([good_extraction(item="cerveja", quantity=3, unit_price=None, stated_total=100.0)]),
        FakeRewrite("reescrita"),
    )
    record = await service.register(b"audio", "audio.m4a", "audio/m4a", db_session)
    assert str(record.unit_price) == "33.33"
    assert str(record.total) == "100.00"


async def test_empty_transcript_raises_without_ai_calls(db_session):
    transcription = FakeTranscription("")
    decision = FakeDecision([good_decision()])
    extraction = FakeExtraction([good_extraction()])
    rewrite = FakeRewrite("algo")
    service = make_service(transcription, decision, extraction, rewrite)
    with pytest.raises(AppError) as exc_info:
        await service.register(b"audio", "audio.m4a", "audio/m4a", db_session)
    assert exc_info.value.code == "NOT_UNDERSTOOD"
    assert decision.calls == 0
    assert extraction.calls == 0
    assert rewrite.calls == 0


async def test_provider_timeout_raises_503(db_session):
    service = make_service(
        FakeTranscription(error=provider_error()),
        FakeDecision([good_decision()]),
        FakeExtraction([good_extraction()]),
        FakeRewrite("algo"),
    )
    with pytest.raises(AppError) as exc_info:
        await service.register(b"audio", "audio.m4a", "audio/m4a", db_session)
    assert exc_info.value.status == 503
    assert exc_info.value.code == "AI_UNAVAILABLE"


async def test_decide_and_extract_start_before_either_finishes(db_session):
    tag = unique_tag()
    extract_started = asyncio.Event()
    service = make_service(
        FakeTranscription(f"cafe {tag}"),
        FakeDecision([good_decision()], wait_for=extract_started),
        FakeExtraction([good_extraction(item=f"dec-{tag}")], started=extract_started),
        FakeRewrite("algo"),
    )
    record = await service.register(b"audio", "audio.m4a", "audio/m4a", db_session)
    assert record.item == f"dec-{tag}"
