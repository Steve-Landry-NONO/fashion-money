from pydantic import BaseModel


class EvaluateIn(BaseModel):
    option_id: str


class EvaluationOut(BaseModel):
    verdict: str
    available: float
    available_after: float
    price: float
    issues: list[dict]


class DecisionActionIn(BaseModel):
    option_id: str
    action: str


class DecisionActionOut(BaseModel):
    decision_id: str
    action: str


class PurchaseConfirmIn(BaseModel):
    option_id: str
    idempotency_key: str


class PurchaseOut(BaseModel):
    purchase_id: str
    wardrobe_item_id: str
    wallet: dict
