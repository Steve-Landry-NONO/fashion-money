import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Capture(Base):
    __tablename__ = "captures"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    image_ref: Mapped[str | None] = mapped_column(String, nullable=True)  # object storage key
    status: Mapped[str] = mapped_column(String, default="processing")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Look(Base):
    __tablename__ = "looks"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    capture_id: Mapped[str] = mapped_column(ForeignKey("captures.id"), index=True)
    style: Mapped[str | None] = mapped_column(String, nullable=True)


class LookPiece(Base):
    __tablename__ = "look_pieces"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    look_id: Mapped[str] = mapped_column(ForeignKey("looks.id"), index=True)
    category: Mapped[str] = mapped_column(String)
    color: Mapped[str | None] = mapped_column(String, nullable=True)
    cut: Mapped[str | None] = mapped_column(String, nullable=True)
    material: Mapped[str | None] = mapped_column(String, nullable=True)
    swatch: Mapped[str | None] = mapped_column(String, nullable=True)
