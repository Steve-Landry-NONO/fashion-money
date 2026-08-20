from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.capture import service
from app.capture.providers import get_decomposition_provider
from app.capture.schemas import CaptureIn, CaptureOut, LookOut, PieceOut
from app.db import get_session
from app.identity.deps import get_current_user
from app.identity.models import User

router = APIRouter(tags=["capture"])


@router.post("/captures", response_model=CaptureOut, status_code=201)
def create_capture(
    body: CaptureIn,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> CaptureOut:
    capture, look = service.create_capture(session, user.id, get_decomposition_provider(), body.image_ref)
    return CaptureOut(capture_id=capture.id, look_id=look.id, status=capture.status)


@router.get("/looks/{look_id}", response_model=LookOut)
def get_look(look_id: str, user: User = Depends(get_current_user), session: Session = Depends(get_session)) -> LookOut:
    try:
        look, pieces, matches = service.get_look_for_user(session, user.id, look_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="look not found") from None
    by_piece = {m.look_piece_id: m for m in matches}
    out = []
    for p in pieces:
        m = by_piece[p.id]
        out.append(PieceOut(
            id=p.id, category=p.category, color=p.color, cut=p.cut, material=p.material, swatch=p.swatch,
            owned_pct=m.owned_pct, is_owned=m.is_owned, match_reason=m.reason,
        ))
    score = round(sum(1 for p in out if p.is_owned) / len(out) * 100) if out else 0
    return LookOut(id=look.id, style=look.style, pieces=out, score_look=score)
