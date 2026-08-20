from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.analytics import emitter
from app.capture.models import Capture, Look, LookPiece
from app.capture.providers import DecompositionProvider
from app.matching.models import Match, WardrobeItem
from app.matching.service import compute_match


def create_capture(
    session: Session,
    user_id: str,
    provider: DecompositionProvider,
    image_ref: str | None = None,
) -> tuple[Capture, Look]:
    capture = Capture(user_id=user_id, image_ref=image_ref, status="processing")
    session.add(capture)
    session.flush()
    emitter.emit(emitter.CAPTURE_STARTED, user_id, source="mock" if image_ref is None else "image_ref")

    decomposed = provider.decompose(image_ref)
    look = Look(capture_id=capture.id, style=decomposed.style)
    session.add(look)
    session.flush()
    for p in decomposed.pieces:
        session.add(LookPiece(
            look_id=look.id,
            category=p.category,
            color=p.color,
            cut=p.cut,
            material=p.material,
            swatch=p.swatch,
        ))
    capture.status = "ready"
    session.commit()
    emitter.emit(emitter.LOOK_DECOMPOSED, user_id, pieces_count=len(decomposed.pieces), style=decomposed.style)
    return capture, look


def get_look_for_user(session: Session, user_id: str, look_id: str) -> tuple[Look, list[LookPiece], list[Match]]:
    look = session.get(Look, look_id)
    if look is None:
        raise ValueError("look not found")
    capture = session.get(Capture, look.capture_id)
    if capture is None or capture.user_id != user_id:
        raise ValueError("look not found")

    pieces = list(session.scalars(select(LookPiece).where(LookPiece.look_id == look_id)).all())
    wardrobe = list(session.scalars(select(WardrobeItem).where(WardrobeItem.user_id == user_id)).all())

    piece_ids = [p.id for p in pieces]
    if piece_ids:
        session.execute(delete(Match).where(Match.look_piece_id.in_(piece_ids)))
    matches: list[Match] = []
    for piece in pieces:
        result = compute_match(piece, wardrobe)
        match = Match(
            look_piece_id=piece.id,
            wardrobe_item_id=result.wardrobe_item_id,
            owned_pct=result.owned_pct,
            is_owned=result.is_owned,
            reason=result.reason,
        )
        session.add(match)
        matches.append(match)
    session.commit()

    owned = sum(1 for m in matches if m.is_owned)
    score = round(owned / len(pieces) * 100) if pieces else 0
    emitter.emit(emitter.MATCH_COMPUTED, user_id, owned_pct=score, regime="j0" if not wardrobe else "mature")
    return look, pieces, matches
