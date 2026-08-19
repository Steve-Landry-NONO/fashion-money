from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_session
from app.identity.deps import get_current_user
from app.identity.models import User
from app.wallet import service
from app.wallet.schemas import BudgetConfigIn, WalletOut

router = APIRouter(tags=["wallet"])


@router.post("/budget", response_model=WalletOut)
def set_budget(body: BudgetConfigIn, user: User = Depends(get_current_user),
               session: Session = Depends(get_session)) -> WalletOut:
    service.set_budget(session, user.id, body.base_amount, body.rollover_cap)
    return WalletOut(**service.get_wallet(session, user.id))


@router.get("/wallet", response_model=WalletOut)
def get_wallet(user: User = Depends(get_current_user),
               session: Session = Depends(get_session)) -> WalletOut:
    try:
        return WalletOut(**service.get_wallet(session, user.id))
    except ValueError:
        raise HTTPException(status_code=404, detail="budget not set") from None
