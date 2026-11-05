from decimal import Decimal

from app.core import pricing
from app.core.pricing import PRICES
from app.services import cost_calculator
from app.services.cost_calculator import audio_cost, format_usd, token_cost, transcribe_cost


def test_decisions_cost_matches_note_example():
    cost = token_cost(PRICES[pricing.DECISIONS_LUNA], 1725, 0, 0, 0)
    assert format_usd(cost) == "0.0001725"


def test_extraction_cost_matches_note_example():
    cost = token_cost(PRICES[pricing.RESPONSES_LUNA], 251, 0, 0, 30)
    assert format_usd(cost) == "0.0000401"


def test_cached_and_write_tokens_discounted_from_uncached():
    cost = token_cost(PRICES[pricing.DECISIONS_LUNA], 1725, 1600, 100, 0)
    assert format_usd(cost) == "0.0000310"


def test_transcription_cost_four_seconds():
    assert transcribe_cost(4.0) is not None
    assert format_usd(transcribe_cost(4.0)) == "0.0003000"


def test_transcription_cost_without_duration_is_none():
    assert transcribe_cost(None) is None


def test_priority_multiplier_doubles_responses_only():
    base = token_cost(PRICES[pricing.RESPONSES_LUNA], 251, 0, 0, 30)
    boosted = token_cost(PRICES[pricing.RESPONSES_LUNA], 251, 0, 0, 30, multiplier=pricing.PRIORITY_MULTIPLIER)
    assert boosted == base * 2
    assert format_usd(boosted) == "0.0000802"


def test_estimated_price_flags():
    assert PRICES[pricing.DECISIONS_LUNA].estimated is False
    assert PRICES[pricing.RESPONSES_LUNA].estimated is False
    assert PRICES[pricing.RESPONSES_MINI].estimated is True
    assert PRICES[pricing.CHAT_DEEPSEEK_FLASH].estimated is True


def test_audio_cost_proportional_to_seconds():
    assert format_usd(audio_cost(Decimal("0.0045"), 8.0)) == "0.0006000"
    assert format_usd(audio_cost(Decimal("0.0045"), 4.0)) == "0.0003000"
