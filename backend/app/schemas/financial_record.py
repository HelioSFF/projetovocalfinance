from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, field_serializer

from app.services.categories import category_label


def format_quantity(value: Decimal) -> str:
    return str(value.normalize())


def format_money(value: Decimal) -> str:
    return f"{value:.2f}"


class FinancialRecordOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    type: str
    category: str
    category_label: str = ""
    item: str
    quantity: Decimal
    unit_price: Decimal
    total: Decimal
    currency: str
    transcript: str
    normalized_text: str | None = None
    created_at: datetime

    @field_serializer("quantity")
    def serialize_quantity(self, value: Decimal) -> str:
        return format_quantity(value)

    @field_serializer("unit_price", "total")
    def serialize_money(self, value: Decimal) -> str:
        return format_money(value)

    @classmethod
    def from_orm_with_label(cls, record) -> "FinancialRecordOut":
        payload = {
            "id": record.id,
            "type": record.type,
            "category": record.category,
            "category_label": category_label(record.category),
            "item": record.item,
            "quantity": record.quantity,
            "unit_price": record.unit_price,
            "total": record.total,
            "currency": record.currency,
            "transcript": record.transcript,
            "normalized_text": record.normalized_text,
            "created_at": record.created_at,
        }
        return cls(**payload)


class FinancialRecordList(BaseModel):
    items: list[FinancialRecordOut]
    limit: int
    offset: int
