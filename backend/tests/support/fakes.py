import asyncio
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

from app.core.errors import ProviderError
from app.schemas.ai import DecisionResult, ExtractionResult


def good_decision(**overrides):
    data = {"plausible": 0.95, "is_financial": 0.95, "record_type": "expense", "category": "food"}
    data.update(overrides)
    return DecisionResult(**data)


def bad_decision(**overrides):
    data = {"plausible": 0.95, "is_financial": 0.1, "record_type": "expense", "category": "food"}
    data.update(overrides)
    return DecisionResult(**data)


def good_extraction(**overrides):
    data = {"item": "café", "quantity": 3, "unit_price": 5.0, "stated_total": 15.0}
    data.update(overrides)
    return ExtractionResult(**data)


class FakeTranscription:
    def __init__(self, text="", error=None):
        self.text = text
        self.error = error
        self.calls = 0

    async def transcribe(self, audio, filename, mime):
        self.calls += 1
        if self.error is not None:
            raise self.error
        return self.text


class FakeDecision:
    def __init__(self, results, started=None, wait_for=None):
        self.results = list(results)
        self.calls = 0
        self.started = started or asyncio.Event()
        self.wait_for = wait_for

    async def decide(self, transcript, attempt=1):
        self.calls += 1
        self.started.set()
        if self.wait_for is not None:
            await asyncio.wait_for(self.wait_for.wait(), 5)
        index = min(self.calls - 1, len(self.results) - 1)
        result = self.results[index]
        if isinstance(result, Exception):
            raise result
        return result


class FakeExtraction:
    def __init__(self, results, started=None):
        self.results = list(results)
        self.calls = 0
        self.started = started or asyncio.Event()

    async def extract(self, transcript, attempt=1):
        self.calls += 1
        self.started.set()
        index = min(self.calls - 1, len(self.results) - 1)
        result = self.results[index]
        if isinstance(result, Exception):
            raise result
        return result


class FakeRewrite:
    def __init__(self, text=""):
        self.text = text
        self.calls = 0

    async def rewrite(self, transcript):
        self.calls += 1
        return self.text


def provider_error():
    return ProviderError()


class FakeVoiceRecordService:
    def __init__(self, record=None, error=None):
        self.record = record
        self.error = error
        self.calls = 0

    async def register(self, audio, filename, mime, session):
        self.calls += 1
        if self.error is not None:
            raise self.error
        return self.record


def usage_namespace(input_tokens=0, cached_tokens=0, cache_write_tokens=0, output_tokens=0, reasoning_tokens=0):
    return SimpleNamespace(
        input_tokens=input_tokens,
        input_tokens_details=SimpleNamespace(cached_tokens=cached_tokens, cache_write_tokens=cache_write_tokens),
        output_tokens=output_tokens,
        output_tokens_details=SimpleNamespace(reasoning_tokens=reasoning_tokens),
    )


def predicate_answer_ns(name, probability):
    return SimpleNamespace(type="predicate", name=name, probability=probability)


def choice_answer_ns(name, choice, confidence, pairs):
    return SimpleNamespace(
        type="choice",
        name=name,
        choice=choice,
        confidence=confidence,
        probabilities=[SimpleNamespace(value=value, probability=probability) for value, probability in pairs],
    )


def refusal_answer_ns(name):
    return SimpleNamespace(type="refusal", name=name)


def decision_response_ns(answers, input_tokens=1725, cached_tokens=0, cache_write_tokens=0):
    return SimpleNamespace(answers=answers, usage=usage_namespace(input_tokens, cached_tokens, cache_write_tokens, 0))


def extraction_response_ns(parsed, input_tokens=251, output_tokens=30):
    return SimpleNamespace(
        output=[
            SimpleNamespace(
                type="message",
                content=[SimpleNamespace(type="output_text", text=json.dumps(parsed))],
            )
        ],
        usage=usage_namespace(input_tokens, 0, 0, output_tokens),
    )


def transcription_result_ns(text, seconds=None):
    usage = SimpleNamespace(type="duration", seconds=seconds) if seconds is not None else None
    return SimpleNamespace(text=text, usage=usage)


def rewrite_response_ns(text, prompt_tokens=43, completion_tokens=8):
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=text))],
        usage=SimpleNamespace(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            prompt_cache_hit_tokens=0,
            prompt_cache_miss_tokens=prompt_tokens,
        ),
    )


def standard_answers_ns(plausible=1.0, financial=1.0, record_type="expense", category="food", category_pairs=None):
    pairs = category_pairs if category_pairs is not None else [(category, 1.0)]
    return [
        predicate_answer_ns("plausible", plausible),
        predicate_answer_ns("is_financial", financial),
        choice_answer_ns("type", record_type, 1.0, [(record_type, 1.0)]),
        choice_answer_ns("category", category, 1.0, pairs),
    ]


class FakeOpenAIClient:
    def __init__(self):
        self.audio = SimpleNamespace(transcriptions=SimpleNamespace(create=AsyncMock()))
        self.decisions = SimpleNamespace(create=AsyncMock())
        self.responses = SimpleNamespace(create=AsyncMock())
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=AsyncMock()))
