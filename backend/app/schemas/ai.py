from dataclasses import dataclass


@dataclass
class DecisionResult:
    plausible: float | None = None
    is_financial: float | None = None
    record_type: str | None = None
    category: str | None = None


@dataclass
class ExtractionResult:
    item: str = ""
    quantity: float | None = None
    unit_price: float | None = None
    stated_total: float | None = None
