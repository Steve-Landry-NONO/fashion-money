from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.analytics import emitter
from app.capture.models import Capture, Look, LookPiece
from app.catalog.models import Option
from app.catalog.providers import get_product_search_provider
from app.catalog.schemas import OptionOut, OptionsOut
from app.db import get_session
from app.identity.deps import get_current_user
from app.identity.models import User
from app.matching.models import Match

router = APIRouter(tags=["catalog"])


def _owned_piece_for_user(session: Session, user_id: str, piece_id: str) -> LookPiece:
    piece = session.get(LookPiece, piece_id)
    if piece is None:
        raise ValueError
    look = session.get(Look, piece.look_id)
    capture = session.get(Capture, look.capture_id) if look else None
    if capture is None or capture.user_id != user_id:
        raise ValueError
    return piece


@router.get("/looks/{look_id}/gaps")
def get_gaps(look_id: str, user: User = Depends(get_current_user), session: Session = Depends(get_session)) -> dict:
    look = session.get(Look, look_id)
    capture = session.get(Capture, look.capture_id) if look else None
    if capture is None or capture.user_id != user.id:
        raise HTTPException(status_code=404, detail="look not found")
    pieces = list(session.scalars(select(LookPiece).where(LookPiece.look_id == look_id)).all())
    ids = [p.id for p in pieces]
    matches = list(session.scalars(select(Match).where(Match.look_piece_id.in_(ids))).all()) if ids else []
    by_piece = {m.look_piece_id: m for m in matches}
    missing = [p.id for p in pieces if p.id not in by_piece or not by_piece[p.id].is_owned]
    emitter.emit(emitter.GAP_IDENTIFIED, user.id, missing_count=len(missing))
    return {"missing": missing}


@router.get("/gaps/{piece_id}/options", response_model=OptionsOut)
def get_options(piece_id: str, user: User = Depends(get_current_user), session: Session = Depends(get_session)) -> OptionsOut:
    try:
        piece = _owned_piece_for_user(session, user.id, piece_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="piece not found") from None
    provider = get_product_search_provider()
    candidates = provider.search(piece, ship_to=user.region)
    session.execute(delete(Option).where(Option.look_piece_id == piece_id))
    rows: list[Option] = []
    for c in candidates:
        row = Option(
            look_piece_id=piece_id, price=c.price, merchant=c.merchant,
            affiliate_url=c.affiliate_url, similarity=c.similarity, purchase_score=c.purchase_score,
        )
        session.add(row)
        rows.append(row)
    session.commit()
    best_id = max(rows, key=lambda r: float(r.purchase_score or 0)).id if rows else None
    emitter.emit(emitter.OPTIONS_VIEWED, user.id, options_count=len(rows))
    return OptionsOut(options=[OptionOut(
        id=r.id, price=float(r.price), merchant=r.merchant, affiliate_url=r.affiliate_url,
        similarity=r.similarity, purchase_score=float(r.purchase_score) if r.purchase_score is not None else None,
        is_best=r.id == best_id,
    ) for r in rows])
