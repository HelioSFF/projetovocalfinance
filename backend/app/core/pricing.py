from dataclasses import dataclass
from decimal import Decimal

DECISIONS_LUNA = "decisions:gpt-6-luna"
RESPONSES_LUNA = "responses:gpt-6-luna"
RESPONSES_MINI = "responses:gpt-4o-mini"
CHAT_DEEPSEEK_FLASH = "chat:deepseek-flash"

TRANSCRIBE_PRICE_PER_MINUTE = Decimal("0.0045")

PRIORITY_MULTIPLIER = Decimal("2")


@dataclass(frozen=True)
class ModelPrice:
    input_per_million: Decimal
    cached_per_million: Decimal
    cache_write_per_million: Decimal
    output_per_million: Decimal
    estimated: bool


PRICES: dict[str, ModelPrice] = {
    DECISIONS_LUNA: ModelPrice(
        input_per_million=Decimal("0.10"),
        cached_per_million=Decimal("0.01"),
        cache_write_per_million=Decimal("0.125"),
        output_per_million=Decimal("0"),
        estimated=False,
    ),
    RESPONSES_LUNA: ModelPrice(
        input_per_million=Decimal("0.10"),
        cached_per_million=Decimal("0.01"),
        cache_write_per_million=Decimal("0.125"),
        output_per_million=Decimal("0.50"),
        estimated=False,
    ),
    RESPONSES_MINI: ModelPrice(
        input_per_million=Decimal("0.15"),
        cached_per_million=Decimal("0.075"),
        cache_write_per_million=Decimal("0"),
        output_per_million=Decimal("0.60"),
        estimated=True,
    ),
    CHAT_DEEPSEEK_FLASH: ModelPrice(
        input_per_million=Decimal("0.30"),
        cached_per_million=Decimal("0.30"),
        cache_write_per_million=Decimal("0"),
        output_per_million=Decimal("1.20"),
        estimated=True,
    ),
}
