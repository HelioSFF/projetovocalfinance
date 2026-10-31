from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.repositories.financial_record_repository import FinancialRecordRepository
from app.schemas.financial_record import FinancialRecordList, FinancialRecordOut

router = APIRouter(prefix="/api")


@router.get("/financial-records", response_model=FinancialRecordList)
async def list_financial_records(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    q: str | None = Query(default=None),
    session: AsyncSession = Depends(get_session),
):
    repository = FinancialRecordRepository(session)
    records = await repository.list_records(limit=limit, offset=offset, query=q)
    items = [FinancialRecordOut.from_orm_with_label(record) for record in records]
    return FinancialRecordList(items=items, limit=limit, offset=offset)
