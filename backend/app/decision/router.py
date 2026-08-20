from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.analytics import emitter
from app.catalog.models import Option
from app.db import get_session
from app.decision import service
from app.decision.schemas import (
    DecisionActionIn,
    DecisionActionOut,
    EvaluateIn,
    EvaluationOut,
    PurchaseConfirmIn,
    PurchaseOut,
)
from app.identity.deps import get_current_user
from app.identity.models import User
from app.wallet.service import get_wallet

router = APIRouter(tags=["decision"])


@router.post("/decisions/evaluate", response_model=EvaluationOut)
def evaluate(
    body: EvaluateIn,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> EvaluationOut:
    option = session.get(Option, body.option_id)
    if option is None:
        raise HTTPException(status_code=404, detail="option not found")
    ev = service.evaluate(session, user.id, option)
    emitter.emit(emitter.DECISION_VIEWED, user.id, verdict=ev.verdict, available=ev.available, price=ev.price)
    return EvaluationOut(**ev.__dict__)


@router.post("/decisions/actions", response_model=DecisionActionOut, status_code=201)
def take_action(
    body: DecisionActionIn,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> DecisionActionOut:
    option = session.get(Option, body.option_id)
    if option is None:
        raise HTTPException(status_code=404, detail="option not found")
    try:
        decision, action = service.record_action(session, user.id, option, body.action)
    except ValueError:
        raise HTTPException(status_code=422, detail="invalid action") from None
    return DecisionActionOut(decision_id=decision.id, action=action.action)


@router.post("/purchases/confirm", response_model=PurchaseOut)
def confirm_purchase(
    body: PurchaseConfirmIn,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> PurchaseOut:
    option = session.get(Option, body.option_id)
    if option is None:
        raise HTTPException(status_code=404, detail="option not found")
    try:
        purchase = service.confirm_purchase(session, user.id, option, body.idempotency_key)
    except Exception:
        session.rollback()
        raise
    wallet = get_wallet(session, user.id)
    assert purchase.wardrobe_item_id is not None
    return PurchaseOut(purchase_id=purchase.id, wardrobe_item_id=purchase.wardrobe_item_id, wallet=wallet)
