"""initial schema (Tech Design §4 + slice refinements)

Revision ID: 0001
Revises:
"""
import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

_money = sa.Numeric(10, 2)
_ts = sa.DateTime(timezone=True)


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("auth_ref", sa.String(), nullable=True),
        sa.Column("region", sa.String(), server_default="EU"),
        sa.Column("created_at", _ts, server_default=sa.func.now()),
    )
    op.create_table(
        "budget_config",
        sa.Column("user_id", sa.String(), sa.ForeignKey("users.id"), primary_key=True),
        sa.Column("base_amount", _money, nullable=False),
        sa.Column("rollover_cap", _money, nullable=False, server_default="0"),
        sa.Column("period_type", sa.String(), server_default="calendar_month"),
        sa.Column("updated_at", _ts, server_default=sa.func.now()),
    )
    op.create_table(
        "budget_ledger",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("user_id", sa.String(), sa.ForeignKey("users.id"), index=True),
        sa.Column("period", sa.String(), index=True),
        sa.Column("type", sa.String()),
        sa.Column("amount", _money),
        sa.Column("ref_purchase_id", sa.String(), nullable=True),
        sa.Column("idempotency_key", sa.String(), nullable=True),
        sa.Column("created_at", _ts, server_default=sa.func.now()),
        sa.UniqueConstraint("user_id", "idempotency_key", name="uq_ledger_idempotency"),
    )
    op.create_index(
        "uq_rollover_once_per_period", "budget_ledger", ["user_id", "period"],
        unique=True, sqlite_where=sa.text("type = 'ROLLOVER_IN'"),
        postgresql_where=sa.text("type = 'ROLLOVER_IN'"),
    )
    op.create_table(
        "wardrobe_items",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("user_id", sa.String(), sa.ForeignKey("users.id"), index=True),
        sa.Column("category", sa.String()),
        sa.Column("color", sa.String(), nullable=True),
        sa.Column("cut", sa.String(), nullable=True),
        sa.Column("material", sa.String(), nullable=True),
        sa.Column("price", _money, nullable=True),
        sa.Column("source", sa.String(), server_default="PHOTO"),
        sa.Column("acquired_at", _ts, server_default=sa.func.now()),
    )
    op.create_table(
        "captures",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("user_id", sa.String(), sa.ForeignKey("users.id"), index=True),
        sa.Column("image_ref", sa.String(), nullable=True),
        sa.Column("status", sa.String(), server_default="processing"),
        sa.Column("created_at", _ts, server_default=sa.func.now()),
    )
    op.create_table(
        "looks",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("capture_id", sa.String(), sa.ForeignKey("captures.id"), index=True),
        sa.Column("style", sa.String(), nullable=True),
    )
    op.create_table(
        "look_pieces",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("look_id", sa.String(), sa.ForeignKey("looks.id"), index=True),
        sa.Column("category", sa.String()),
        sa.Column("color", sa.String(), nullable=True),
        sa.Column("cut", sa.String(), nullable=True),
        sa.Column("material", sa.String(), nullable=True),
        sa.Column("swatch", sa.String(), nullable=True),
    )
    op.create_table(
        "matches",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("look_piece_id", sa.String(), sa.ForeignKey("look_pieces.id"), index=True),
        sa.Column("wardrobe_item_id", sa.String(), sa.ForeignKey("wardrobe_items.id"), nullable=True),
        sa.Column("owned_pct", sa.Integer(), server_default="0"),
        sa.Column("is_owned", sa.Boolean(), server_default=sa.false()),
        sa.Column("reason", sa.String(), nullable=True),
    )
    op.create_table(
        "options",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("look_piece_id", sa.String(), sa.ForeignKey("look_pieces.id"), index=True),
        sa.Column("price", _money),
        sa.Column("merchant", sa.String(), nullable=True),
        sa.Column("affiliate_url", sa.String(), nullable=True),
        sa.Column("similarity", sa.Integer(), nullable=True),
        sa.Column("purchase_score", sa.Numeric(6, 3), nullable=True),
    )
    op.create_table(
        "decisions",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("user_id", sa.String(), sa.ForeignKey("users.id"), index=True),
        sa.Column("look_id", sa.String(), sa.ForeignKey("looks.id"), nullable=True),
        sa.Column("option_id", sa.String(), sa.ForeignKey("options.id"), nullable=True),
        sa.Column("verdict", sa.String(), nullable=True),
        sa.Column("available_at", _money, nullable=True),
        sa.Column("price", _money, nullable=True),
        sa.Column("created_at", _ts, server_default=sa.func.now()),
    )
    op.create_table(
        "decision_actions",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("decision_id", sa.String(), sa.ForeignKey("decisions.id"), index=True),
        sa.Column("action", sa.String()),
        sa.Column("created_at", _ts, server_default=sa.func.now()),
    )
    op.create_table(
        "purchases",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("user_id", sa.String(), sa.ForeignKey("users.id"), index=True),
        sa.Column("option_id", sa.String(), sa.ForeignKey("options.id")),
        sa.Column("price", _money),
        sa.Column("confirmed_at", _ts, server_default=sa.func.now()),
        sa.Column("wardrobe_item_id", sa.String(), sa.ForeignKey("wardrobe_items.id"), nullable=True),
    )


def downgrade() -> None:
    for t in [
        "purchases", "decision_actions", "decisions", "options", "matches",
        "look_pieces", "looks", "captures", "wardrobe_items", "budget_ledger",
        "budget_config", "users",
    ]:
        op.drop_table(t)
