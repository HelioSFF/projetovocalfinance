import os
import uuid

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text

pytestmark = pytest.mark.migrations


def alembic_config(database_url: str) -> Config:
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", database_url)
    return config


def split_target(base_async_url: str, db_name: str) -> tuple[str, str]:
    prefix = base_async_url.rsplit("/", 1)[0]
    async_url = f"{prefix}/{db_name}"
    sync_url = async_url.replace("postgresql+asyncpg://", "postgresql://")
    return async_url, sync_url


def test_upgrade_clean_and_reapply(monkeypatch):
    base_async_url = os.getenv("TEST_MIGRATION_DATABASE_URL", "")
    if not base_async_url:
        raise RuntimeError("TEST_MIGRATION_DATABASE_URL is not configured")
    suffix = uuid.uuid4().hex[:8]
    db_name = f"vocal_mig_{suffix}"
    admin_sync_url = base_async_url.replace("postgresql+asyncpg://", "postgresql://").rsplit("/", 1)[0] + "/postgres"
    target_async_url, target_sync_url = split_target(base_async_url, db_name)
    admin_engine = create_engine(admin_sync_url, isolation_level="AUTOCOMMIT")
    with admin_engine.connect() as connection:
        connection.execute(text(f'CREATE DATABASE "{db_name}"'))
    admin_engine.dispose()
    try:
        monkeypatch.setenv("DATABASE_URL", target_async_url)
        command.upgrade(alembic_config(target_async_url), "head")
        engine = create_engine(target_sync_url)
        try:
            inspector = inspect(engine)
            assert "financial_records" in inspector.get_table_names()
            indexes = {index["name"] for index in inspector.get_indexes("financial_records")}
            assert "ix_financial_records_created_at" in indexes
        finally:
            engine.dispose()
        command.upgrade(alembic_config(target_async_url), "head")
        command.downgrade(alembic_config(target_async_url), "-1")
        engine = create_engine(target_sync_url)
        try:
            assert "financial_records" not in inspect(engine).get_table_names()
        finally:
            engine.dispose()
        command.upgrade(alembic_config(target_async_url), "head")
    finally:
        cleanup_engine = create_engine(admin_sync_url, isolation_level="AUTOCOMMIT")
        with cleanup_engine.connect() as connection:
            connection.execute(
                text(
                    "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                    f"WHERE datname = '{db_name}' AND pid <> pg_backend_pid()"
                )
            )
            connection.execute(text(f'DROP DATABASE IF EXISTS "{db_name}"'))
        cleanup_engine.dispose()
