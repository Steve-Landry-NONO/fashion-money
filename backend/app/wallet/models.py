import uuid
from datetime import datetime

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base

# NOTE (V1 simplification): money stored as Numeric(10,2). A hardening ticket
# should move to integer minor units to remove any float rounding risk.


class BudgetConfig(Base):
    __tablename__ = "budget_config"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), primary_key=True)
    base_amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    rollover_cap: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    period_type: Mapped[str] = mapped_column(String, default="calendar_month")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class BudgetLedger(Base):
    """Append-only. Balance is derived, never stored (VS-05)."""

    __tablename__ = "budget_ledger"
    __table_args__ = (
        # Refinement (3): a rollover can be credited AT MOST ONCE per period.
        # Partial unique index — applies only to ROLLOVER_IN, so multiple
        # SPEND/ADJUST rows per period remain allowed.
        Index(
            "uq_rollover_once_per_period", "user_id", "period", unique=True,
            sqlite_where=text("type = 'ROLLOVER_IN'"),
            postgresql_where=text("type = 'ROLLOVER_IN'"),
        ),
        # Refinement (2): idempotency key makes /purchases/confirm replay-safe.
        # NULL keys are distinct in both SQLite and Postgres, so unrelated
        # entries without a key are unaffected.
        UniqueConstraint("user_id", "idempotency_key", name="uq_ledger_idempotency"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    period: Mapped[str] = mapped_column(String, index=True)  # e.g. "2026-08"
    type: Mapped[str] = mapped_column(String)  # SPEND | ADJUST | ROLLOVER_IN
    amount: Mapped[float] = mapped_column(Numeric(10, 2))  # always positive
    ref_purchase_id: Mapped[str | None] = mapped_column(String, nullable=True)
    idempotency_key: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
