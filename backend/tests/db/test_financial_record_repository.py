from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.models.financial_record import FinancialRecord
from app.repositories.financial_record_repository import FinancialRecordRepository
from tests.support.factories import create_record, record_kwargs, unique_tag


async def test_create_persists_record(db_session):
    kwargs = record_kwargs()
    record = FinancialRecord(**kwargs)
    db_session.add(record)
    await db_session.commit()
    await db_session.refresh(record)
    assert record.id is not None
    assert record.item == kwargs["item"]
    assert record.currency == "BRL"


async def test_list_orders_by_created_at_desc(db_session):
    tag = unique_tag()
    base = datetime.now(timezone.utc)
    first = await create_record(db_session, item=f"cafe-{tag}-a", transcript=f"t {tag} a", created_at=base - timedelta(seconds=30))
    second = await create_record(db_session, item=f"cafe-{tag}-b", transcript=f"t {tag} b", created_at=base - timedelta(seconds=10))
    third = await create_record(db_session, item=f"cafe-{tag}-c", transcript=f"t {tag} c", created_at=base)
    repository = FinancialRecordRepository(db_session)
    records = await repository.list_records(limit=10, offset=0, query=f"cafe-{tag}")
    assert [record.id for record in records] == [third.id, second.id, first.id]


async def test_search_filters_by_item(db_session):
    tag = unique_tag()
    wanted = await create_record(db_session, item=f"cafe-{tag}", transcript=f"t {tag}")
    await create_record(db_session)
    repository = FinancialRecordRepository(db_session)
    records = await repository.list_records(limit=10, offset=0, query=f"cafe-{tag}")
    assert [record.id for record in records] == [wanted.id]


async def test_limit_and_offset_with_query(db_session):
    tag = unique_tag()
    created = []
    for index in range(5):
        created.append(await create_record(db_session, item=f"cafe-{tag}-{index}", transcript=f"t {tag} {index}"))
    repository = FinancialRecordRepository(db_session)
    first_page = await repository.list_records(limit=2, offset=0, query=f"cafe-{tag}")
    second_page = await repository.list_records(limit=2, offset=2, query=f"cafe-{tag}")
    assert len(first_page) == 2
    assert len(second_page) == 2
    assert {record.id for record in first_page}.isdisjoint({record.id for record in second_page})


async def test_quantity_check_rejects_zero(db_session):
    record = FinancialRecord(**record_kwargs(quantity=Decimal("0")))
    db_session.add(record)
    with pytest.raises(IntegrityError):
        await db_session.commit()
    await db_session.rollback()
