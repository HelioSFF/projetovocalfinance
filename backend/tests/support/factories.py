import uuid
from datetime import datetime, timezone
from decimal import Decimal

from app.models.financial_record import FinancialRecord


def unique_tag() -> str:
    return uuid.uuid4().hex[:8]


def record_kwargs(**overrides):
    tag = unique_tag()
    data = {
        "type": "expense",
        "category": "food",
        "item": f"cafe-{tag}",
        "quantity": Decimal("3"),
        "unit_price": Decimal("5.00"),
        "total": Decimal("15.00"),
        "currency": "BRL",
        "transcript": f"comprei cafe {tag}",
        "normalized_text": None,
        "created_at": datetime.now(timezone.utc),
    }
    data.update(overrides)
    return data


async def create_record(session, **overrides):
    record = FinancialRecord(**record_kwargs(**overrides))
    session.add(record)
    await session.commit()
    await session.refresh(record)
    return record
