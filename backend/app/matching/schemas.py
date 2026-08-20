from pydantic import BaseModel


class WardrobeItemIn(BaseModel):
    category: str
    color: str | None = None
    cut: str | None = None
    material: str | None = None
    price: float | None = None
    source: str = "PHOTO"


class WardrobeItemOut(WardrobeItemIn):
    id: str
