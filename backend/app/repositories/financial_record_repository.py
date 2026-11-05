from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.financial_record import FinancialRecord


class FinancialRecordRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        record_type: str,
        category: str,
        item: str,
        quantity,
        unit_price,
        total,
        transcript: str,
        normalized_text: str | None,
    ) -> FinancialRecord:
        record = FinancialRecord(
            type=record_type,
            category=category,
            item=item,
            quantity=quantity,
            unit_price=unit_price,
            total=total,
            currency="BRL",
            transcript=transcript,
            normalized_text=normalized_text,
        )
        self.session.add(record)
        await self.session.commit()
        await self.session.refresh(record)
        return record

    async def list_records(self, limit: int, offset: int, query: str | None = None) -> list[FinancialRecord]:
        statement = select(FinancialRecord).order_by(FinancialRecord.created_at.desc(), FinancialRecord.id.desc())
        if query:
            statement = statement.where(FinancialRecord.item.ilike(f"%{query}%"))
        statement = statement.limit(limit).offset(offset)
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def count_records(self, query: str | None = None) -> int:
        statement = select(func.count()).select_from(FinancialRecord)
        if query:
            statement = statement.where(FinancialRecord.item.ilike(f"%{query}%"))
        result = await self.session.execute(statement)
        return int(result.scalar_one())
