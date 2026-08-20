from pydantic import BaseModel


class OptionOut(BaseModel):
    id: str
    price: float
    merchant: str | None
    affiliate_url: str | None
    similarity: int | None
    purchase_score: float | None
    is_best: bool


class OptionsOut(BaseModel):
    options: list[OptionOut]
