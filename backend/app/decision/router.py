from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.analytics import emitter
from app.analytics.context import context_for_option
from app.catalog.models import Option
from app.catalog.providers import candidate_from_option, get_product_search_provider
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


def _revalidate_option(session: Session, option: Option) -> None:
    if not option.provider or option.provider == "mock":
        return
    if option.fetched_at is None:
        raise HTTPException(status_code=409, detail="option cannot be revalidated")
    provider = get_product_search_provider(option.provider)
    try:
        candidate = candidate_from_option(option)
    except ValueError:
        raise HTTPException(status_code=409, detail="option cannot be revalidated") from None
    verified = provider.verify(candidate)
    if verified is None:
        option.is_available = False
        session.commit()
        raise HTTPException(status_code=409, detail="option no longer available")

    option.price = verified.price
    option.currency = verified.currency
    option.merchant = verified.merchant
    option.product_url = verified.product_url
    option.affiliate_url = verified.affiliate_url
    option.checkout_url = verified.checkout_url
    option.image_url = verified.image_url
    option.availability = verified.availability
    option.is_available = verified.is_available
    option.fetched_at = verified.fetched_at
    option.expires_at = verified.expires_at
    session.commit()


@router.post("/decisions/evaluate", response_model=EvaluationOut)
def evaluate(
    body: EvaluateIn,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> EvaluationOut:
    option = session.get(Option, body.option_id)
    if option is None:
        raise HTTPException(status_code=404, detail="option not found")
    _revalidate_option(session, option)
    ev = service.evaluate(session, user.id, option)
    ctx = context_for_option(session, user.id, option)
    emitter.emit(
        emitter.DECISION_VIEWED,
        user.id,
        verdict=ev.verdict,
        available=ev.available,
        available_after=ev.available_after,
        price=ev.price,
        capture_index=ctx.capture_index,
        wardrobe_count=ctx.wardrobe_count,
        regime=ctx.regime,
    )
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
