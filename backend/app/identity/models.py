import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    auth_ref: Mapped[str | None] = mapped_column(String, nullable=True)
    region: Mapped[str] = mapped_column(String, default="EU")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
