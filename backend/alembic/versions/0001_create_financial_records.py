"""create financial_records."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

TABLE_NAME = "financial_records"
INDEX_NAME = "ix_financial_records_created_at"


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if TABLE_NAME in inspector.get_table_names():
        existing_indexes = {index["name"] for index in inspector.get_indexes(TABLE_NAME)}
        if INDEX_NAME not in existing_indexes:
            op.create_index(INDEX_NAME, TABLE_NAME, [sa.text("created_at DESC")])
        return
    op.create_table(
        TABLE_NAME,
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("type", sa.String(10), nullable=False),
        sa.Column("category", sa.String(40), nullable=False),
        sa.Column("item", sa.String(120), nullable=False),
        sa.Column("quantity", sa.Numeric(12, 3), nullable=False),
        sa.Column("unit_price", sa.Numeric(12, 2), nullable=False),
        sa.Column("total", sa.Numeric(14, 2), nullable=False),
        sa.Column("currency", sa.CHAR(3), nullable=False, server_default="BRL"),
        sa.Column("transcript", sa.Text(), nullable=False),
        sa.Column("normalized_text", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("type IN ('income','expense')", name="ck_financial_records_type"),
        sa.CheckConstraint("quantity > 0", name="ck_financial_records_quantity_positive"),
        sa.CheckConstraint("unit_price > 0", name="ck_financial_records_unit_price_positive"),
        sa.CheckConstraint("total > 0", name="ck_financial_records_total_positive"),
    )
    op.create_index(INDEX_NAME, TABLE_NAME, [sa.text("created_at DESC")])


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if TABLE_NAME not in inspector.get_table_names():
        return
    existing_indexes = {index["name"] for index in inspector.get_indexes(TABLE_NAME)}
    if INDEX_NAME in existing_indexes:
        op.drop_index(INDEX_NAME, table_name=TABLE_NAME)
    op.drop_table(TABLE_NAME)
