"""persist rich product option contract

Revision ID: 0004_product_option_contract
Revises: 0003_collage_vision_contract
"""

import sqlalchemy as sa
from alembic import op

revision = "0004_product_option_contract"
down_revision = "0003_collage_vision_contract"
branch_labels = None
depends_on = None


COLUMNS = [
    sa.Column("provider", sa.String(), nullable=True),
    sa.Column("external_id", sa.String(), nullable=True),
    sa.Column("variant_id", sa.String(), nullable=True),
    sa.Column("name", sa.String(), nullable=True),
    sa.Column("currency", sa.String(), nullable=True),
    sa.Column("product_url", sa.String(), nullable=True),
    sa.Column("checkout_url", sa.String(), nullable=True),
    sa.Column("image_url", sa.String(), nullable=True),
    sa.Column("original_price", sa.Numeric(10, 2), nullable=True),
    sa.Column("shipping_price", sa.Numeric(10, 2), nullable=True),
    sa.Column("availability", sa.String(), nullable=True),
    sa.Column("is_available", sa.Boolean(), nullable=True),
    sa.Column("brand", sa.String(), nullable=True),
    sa.Column("size", sa.String(), nullable=True),
    sa.Column("color", sa.String(), nullable=True),
    sa.Column("cut", sa.String(), nullable=True),
    sa.Column("material", sa.String(), nullable=True),
    sa.Column("raw_category", sa.String(), nullable=True),
    sa.Column("condition", sa.String(), nullable=True),
    sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=True),
    sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
]


def upgrade() -> None:
    for column in COLUMNS:
        op.add_column("options", column)


def downgrade() -> None:
    for column in reversed(COLUMNS):
        op.drop_column("options", column.name)
