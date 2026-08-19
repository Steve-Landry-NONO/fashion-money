import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class WardrobeItem(Base):
    __tablename__ = "wardrobe_items"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    category: Mapped[str] = mapped_column(String)
    color: Mapped[str | None] = mapped_column(String, nullable=True)
    cut: Mapped[str | None] = mapped_column(String, nullable=True)
    material: Mapped[str | None] = mapped_column(String, nullable=True)
    price: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    source: Mapped[str] = mapped_column(String, default="PHOTO")  # PHOTO|RECEIPT|PURCHASE
    acquired_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Match(Base):
    __tablename__ = "matches"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    look_piece_id: Mapped[str] = mapped_column(ForeignKey("look_pieces.id"), index=True)
    wardrobe_item_id: Mapped[str | None] = mapped_column(ForeignKey("wardrobe_items.id"), nullable=True)
    owned_pct: Mapped[int] = mapped_column(default=0)
    is_owned: Mapped[bool] = mapped_column(Boolean, default=False)
    reason: Mapped[str | None] = mapped_column(String, nullable=True)  # debuggable: which attrs matched
