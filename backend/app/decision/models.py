import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Numeric, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Decision(Base):
    __tablename__ = "decisions"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    look_id: Mapped[str | None] = mapped_column(ForeignKey("looks.id"), nullable=True)
    option_id: Mapped[str | None] = mapped_column(ForeignKey("options.id"), nullable=True)
    verdict: Mapped[str | None] = mapped_column(String, nullable=True)
    available_at: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    price: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class DecisionAction(Base):
    __tablename__ = "decision_actions"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    decision_id: Mapped[str] = mapped_column(ForeignKey("decisions.id"), index=True)
    action: Mapped[str] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Purchase(Base):
    __tablename__ = "purchases"
    __table_args__ = (UniqueConstraint("user_id", "idempotency_key", name="uq_purchase_idempotency"),)
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    option_id: Mapped[str] = mapped_column(ForeignKey("options.id"))
    price: Mapped[float] = mapped_column(Numeric(10, 2))
    idempotency_key: Mapped[str] = mapped_column(String)
    confirmed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    wardrobe_item_id: Mapped[str | None] = mapped_column(ForeignKey("wardrobe_items.id"), nullable=True)
