from pydantic import BaseModel, Field


class BudgetConfigIn(BaseModel):
    base_amount: float = Field(gt=0)
    rollover_cap: float | None = None  # defaults to cap_multiplier * base


class WalletOut(BaseModel):
    period: str
    base: float
    rollover_in: float
    spent: float
    available: float
