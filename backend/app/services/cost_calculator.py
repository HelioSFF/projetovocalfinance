from decimal import Decimal, ROUND_HALF_UP

from app.core.pricing import ModelPrice, TRANSCRIBE_PRICE_PER_MINUTE

USD_PLACES = Decimal("0.0000001")
TOKENS_PER_MILLION = Decimal("1000000")


def token_cost(
    price: ModelPrice,
    input_tokens: int,
    cached_tokens: int,
    cache_write_tokens: int,
    output_tokens: int,
    multiplier: Decimal = Decimal(1),
) -> Decimal:
    uncached = max(0, input_tokens - cached_tokens - cache_write_tokens)
    total = (
        Decimal(uncached) * price.input_per_million
        + Decimal(cached_tokens) * price.cached_per_million
        + Decimal(cache_write_tokens) * price.cache_write_per_million
        + Decimal(output_tokens) * price.output_per_million
    )
    return total * multiplier / TOKENS_PER_MILLION


def audio_cost(price_per_minute: Decimal, seconds: float) -> Decimal:
    return Decimal(str(seconds)) / Decimal(60) * price_per_minute


def transcribe_cost(seconds: float | None) -> Decimal | None:
    if seconds is None:
        return None
    return audio_cost(TRANSCRIBE_PRICE_PER_MINUTE, seconds)


def format_usd(value: Decimal) -> str:
    return str(value.quantize(USD_PLACES, rounding=ROUND_HALF_UP))
