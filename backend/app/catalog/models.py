import uuid

from sqlalchemy import ForeignKey, Numeric, String
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
