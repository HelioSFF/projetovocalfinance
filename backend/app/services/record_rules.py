import re
from decimal import Decimal, ROUND_HALF_UP

from app.schemas.ai import DecisionResult, ExtractionResult
from app.services.categories import CATEGORIES

CATEGORY_TYPES = {entry["code"]: entry["type"] for entry in CATEGORIES}

NOT_UNDERSTOOD = "NOT_UNDERSTOOD"
NOT_FINANCIAL = "NOT_FINANCIAL"


def is_accepted(decision: DecisionResult, extraction: ExtractionResult | None, threshold: float) -> bool:
    if decision.plausible is None or decision.is_financial is None:
        return False
    if decision.plausible < threshold or decision.is_financial < threshold:
        return False
    if extraction is None:
        return False
    if not extraction.item or not extraction.item.strip():
        return False
    if extraction.quantity is None or extraction.quantity <= 0:
        return False
    unit_price = extraction.unit_price or 0
    stated_total = extraction.stated_total or 0
    return unit_price > 0 or stated_total > 0


TOTAL_WORDS = ("em", "total", "totais", "ao todo", "tudo")


def mentions_total(transcript: str) -> bool:
    lowered = transcript.lower()
    return any(re.search(rf"\b{re.escape(word)}\b", lowered) for word in TOTAL_WORDS)


def resolve_prices(
    transcript: str, quantity: float | None, unit_price: float | None, stated_total: float | None
) -> tuple[float | None, float | None]:
    unit = unit_price if unit_price is not None and unit_price > 0 else None
    stated = stated_total if stated_total is not None and stated_total > 0 else None
    if unit is None and stated is not None and (quantity or 0) > 1 and not mentions_total(transcript):
        return stated, None
    return unit, stated


def compute_amounts(quantity: float, unit_price: float | None, stated_total: float | None) -> tuple[Decimal, Decimal, Decimal]:
    amount_quantity = Decimal(str(quantity)).quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)
    if amount_quantity <= 0:
        raise ValueError("quantity must be positive")
    if unit_price is not None and unit_price > 0:
        amount_unit_price = Decimal(str(unit_price)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        amount_total = (amount_quantity * amount_unit_price).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        return amount_quantity, amount_unit_price, amount_total
    if stated_total is not None and stated_total > 0:
        amount_total = Decimal(str(stated_total)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        amount_unit_price = (amount_total / amount_quantity).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        return amount_quantity, amount_unit_price, amount_total
    raise ValueError("unit_price or stated_total must be positive")


def reconcile_type_category(record_type: str | None, category: str | None) -> tuple[str, str]:
    fallback = "other_income" if record_type == "income" else "other_expense"
    if record_type not in ("income", "expense"):
        return "expense", "other_expense"
    if category is None or CATEGORY_TYPES.get(category) != record_type:
        return record_type, fallback
    return record_type, category


def failure_code(decision: DecisionResult, threshold: float) -> str:
    if decision.plausible is not None and decision.plausible >= threshold:
        if decision.is_financial is not None and decision.is_financial < threshold:
            return NOT_FINANCIAL
    return NOT_UNDERSTOOD
