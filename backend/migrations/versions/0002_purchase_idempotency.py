"""purchase idempotency key

Revision ID: 0002_purchase_idempotency
Revises: 0001_initial
"""
from alembic import op
import sqlalchemy as sa

revision = "0002_purchase_idempotency"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("purchases", sa.Column("idempotency_key", sa.String(), nullable=True))
    op.create_unique_constraint("uq_purchase_idempotency", "purchases", ["user_id", "idempotency_key"])


def downgrade() -> None:
    op.drop_constraint("uq_purchase_idempotency", "purchases", type_="unique")
    op.drop_column("purchases", "idempotency_key")
