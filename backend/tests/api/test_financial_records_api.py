from app.core.errors import AppError
from app.db.session import get_session
from app.main import app
from tests.support.factories import create_record, unique_tag


async def test_health_returns_ok(client):
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


async def test_list_returns_items_with_strings(client, db_session):
    tag = unique_tag()
    first = await create_record(db_session, item=f"cafe-{tag}-1", transcript=f"t {tag} 1")
    second = await create_record(db_session, item=f"cafe-{tag}-2", transcript=f"t {tag} 2")
    response = await client.get("/api/financial-records", params={"q": f"cafe-{tag}", "limit": 50, "offset": 0})
    assert response.status_code == 200
    payload = response.json()
    assert payload["limit"] == 50
    assert payload["offset"] == 0
    ids = {item["id"] for item in payload["items"]}
    assert {str(first.id), str(second.id)} == ids
    sample = payload["items"][0]
    assert sample["quantity"] == "3"
    assert sample["unit_price"] == "5.00"
    assert sample["total"] == "15.00"
    assert sample["category_label"] == "Alimentação"


async def test_list_search_filters_by_q(client, db_session):
    tag = unique_tag()
    wanted = await create_record(db_session, item=f"cafe-{tag}", transcript=f"t {tag}")
    await create_record(db_session)
    response = await client.get("/api/financial-records", params={"q": f"cafe-{tag}"})
    assert response.status_code == 200
    assert [item["id"] for item in response.json()["items"]] == [str(wanted.id)]


async def test_list_limit_out_of_range_returns_422(client):
    assert (await client.get("/api/financial-records", params={"limit": 0})).status_code == 422
    assert (await client.get("/api/financial-records", params={"limit": 101})).status_code == 422
    assert (await client.get("/api/financial-records", params={"offset": -1})).status_code == 422


async def test_app_error_format(client):
    async def failing_session():
        raise AppError("DB_UNAVAILABLE", "Banco de dados indisponível.", 503)
        yield None

    app.dependency_overrides[get_session] = failing_session
    try:
        response = await client.get("/health")
    finally:
        app.dependency_overrides.pop(get_session, None)
    assert response.status_code == 503
    assert response.json() == {"error": {"code": "DB_UNAVAILABLE", "message": "Banco de dados indisponível."}}
