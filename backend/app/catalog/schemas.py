from datetime import datetime

from pydantic import BaseModel


class OptionOut(BaseModel):
    id: str
    price: float
    merchant: str | None
    affiliate_url: str | None
    similarity: int | None
    purchase_score: float | None
    is_best: bool
    name: str | None = None
    currency: str | None = None
    product_url: str | None = None
    checkout_url: str | None = None
    image_url: str | None = None
    availability: str | None = None
    is_available: bool | None = None
    fetched_at: datetime | None = None


class OptionsOut(BaseModel):
    options: list[OptionOut]
