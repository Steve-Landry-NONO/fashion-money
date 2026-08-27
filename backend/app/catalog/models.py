import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Option(Base):
    __tablename__ = "options"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    look_piece_id: Mapped[str] = mapped_column(ForeignKey("look_pieces.id"), index=True)
    price: Mapped[float] = mapped_column(Numeric(10, 2))
    merchant: Mapped[str | None] = mapped_column(String, nullable=True)
    affiliate_url: Mapped[str | None] = mapped_column(String, nullable=True)
    similarity: Mapped[int | None] = mapped_column(nullable=True)
    purchase_score: Mapped[float | None] = mapped_column(Numeric(6, 3), nullable=True)

    provider: Mapped[str | None] = mapped_column(String, nullable=True)
    external_id: Mapped[str | None] = mapped_column(String, nullable=True)
    variant_id: Mapped[str | None] = mapped_column(String, nullable=True)
    name: Mapped[str | None] = mapped_column(String, nullable=True)
    currency: Mapped[str | None] = mapped_column(String, nullable=True)
    product_url: Mapped[str | None] = mapped_column(String, nullable=True)
    checkout_url: Mapped[str | None] = mapped_column(String, nullable=True)
    image_url: Mapped[str | None] = mapped_column(String, nullable=True)
    original_price: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    shipping_price: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    availability: Mapped[str | None] = mapped_column(String, nullable=True)
    is_available: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    brand: Mapped[str | None] = mapped_column(String, nullable=True)
    size: Mapped[str | None] = mapped_column(String, nullable=True)
    color: Mapped[str | None] = mapped_column(String, nullable=True)
    cut: Mapped[str | None] = mapped_column(String, nullable=True)
    material: Mapped[str | None] = mapped_column(String, nullable=True)
    raw_category: Mapped[str | None] = mapped_column(String, nullable=True)
    condition: Mapped[str | None] = mapped_column(String, nullable=True)
    fetched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
