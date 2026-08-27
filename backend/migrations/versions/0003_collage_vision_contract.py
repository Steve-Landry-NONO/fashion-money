"""persist collage-aware vision contract

Revision ID: 0003_collage_vision_contract
Revises: 0002_purchase_idempotency
"""

import sqlalchemy as sa
from alembic import op

revision = "0003_collage_vision_contract"
down_revision = "0002_purchase_idempotency"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("looks", sa.Column("image_type", sa.String(), nullable=False, server_default="single_outfit"))
    op.add_column("looks", sa.Column("dominant_palette", sa.JSON(), nullable=False, server_default=sa.text("'[]'")))
    op.add_column("looks", sa.Column("representative_outfit_index", sa.Integer(), nullable=False, server_default="0"))

    op.create_table(
        "look_outfits",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("look_id", sa.String(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("style", sa.String(), nullable=True),
        sa.Column("is_representative", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.ForeignKeyConstraint(["look_id"], ["looks.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_look_outfits_look_id", "look_outfits", ["look_id"], unique=False)

    op.add_column("look_pieces", sa.Column("outfit_id", sa.String(), nullable=True))
    op.add_column("look_pieces", sa.Column("category_raw", sa.String(), nullable=True))
    op.add_column("look_pieces", sa.Column("confidence", sa.Float(), nullable=True))
    op.create_foreign_key(
        "fk_look_pieces_outfit_id",
        "look_pieces",
        "look_outfits",
        ["outfit_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index("ix_look_pieces_outfit_id", "look_pieces", ["outfit_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_look_pieces_outfit_id", table_name="look_pieces")
    op.drop_constraint("fk_look_pieces_outfit_id", "look_pieces", type_="foreignkey")
    op.drop_column("look_pieces", "confidence")
    op.drop_column("look_pieces", "category_raw")
    op.drop_column("look_pieces", "outfit_id")

    op.drop_index("ix_look_outfits_look_id", table_name="look_outfits")
    op.drop_table("look_outfits")

    op.drop_column("looks", "representative_outfit_index")
    op.drop_column("looks", "dominant_palette")
    op.drop_column("looks", "image_type")
