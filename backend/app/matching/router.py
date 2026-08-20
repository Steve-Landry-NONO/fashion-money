from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.analytics import emitter
from app.analytics.context import regime_for_wardrobe, wardrobe_count
from app.db import get_session
from app.identity.deps import get_current_user
from app.identity.models import User
from app.matching.models import WardrobeItem
from app.matching.schemas import WardrobeItemIn, WardrobeItemOut

router = APIRouter(tags=["wardrobe"])


@router.post("/wardrobe/items", response_model=WardrobeItemOut, status_code=201)
def add_item(
    body: WardrobeItemIn,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> WardrobeItemOut:
    item = WardrobeItem(user_id=user.id, **body.model_dump())
    session.add(item)
    session.commit()
    count = wardrobe_count(session, user.id)
    emitter.emit(
        emitter.WARDROBE_ITEM_ADDED,
        user.id,
        source=body.source,
        category=body.category,
        wardrobe_count=count,
        regime=regime_for_wardrobe(count),
    )
    return WardrobeItemOut(id=item.id, **body.model_dump())


@router.get("/wardrobe", response_model=list[WardrobeItemOut])
def get_wardrobe(
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> list[WardrobeItemOut]:
    rows = list(session.scalars(select(WardrobeItem).where(WardrobeItem.user_id == user.id)).all())
    return [
        WardrobeItemOut(
            id=r.id,
            category=r.category,
            color=r.color,
            cut=r.cut,
            material=r.material,
            price=float(r.price) if r.price is not None else None,
            source=r.source,
        )
        for r in rows
    ]
