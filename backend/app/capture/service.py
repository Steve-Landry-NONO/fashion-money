from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.analytics import emitter
from app.analytics.context import context_for_capture
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
    ctx = context_for_capture(session, user_id, capture)
    emitter.emit(
        emitter.CAPTURE_STARTED,
        user_id,
        source="mock" if image_ref is None else "image_ref",
        capture_index=ctx.capture_index,
        wardrobe_count=ctx.wardrobe_count,
        regime=ctx.regime,
    )
    if (ctx.capture_index or 0) > 1:
        emitter.emit(
            emitter.RETURN_SESSION,
            user_id,
            capture_index=ctx.capture_index,
            wardrobe_count=ctx.wardrobe_count,
            regime=ctx.regime,
        )

    decomposed = provider.decompose(image_ref)
    look = Look(capture_id=capture.id, style=decomposed.style)
    session.add(look)
    session.flush()
    for p in decomposed.pieces:
        session.add(
            LookPiece(
                look_id=look.id,
                category=p.category,
                color=p.color,
                cut=p.cut,
                material=p.material,
                swatch=p.swatch,
            )
        )
    capture.status = "ready"
    session.commit()
    emitter.emit(
        emitter.LOOK_DECOMPOSED,
        user_id,
        pieces_count=len(decomposed.pieces),
        style=decomposed.style,
        capture_index=ctx.capture_index,
        wardrobe_count=ctx.wardrobe_count,
        regime=ctx.regime,
    )
    return capture, look


def get_look_for_user(
    session: Session,
    user_id: str,
    look_id: str,
) -> tuple[Look, list[LookPiece], list[Match]]:
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
    ctx = context_for_capture(session, user_id, capture)
    emitter.emit(
        emitter.MATCH_COMPUTED,
        user_id,
        owned_pct=score,
        capture_index=ctx.capture_index,
        wardrobe_count=ctx.wardrobe_count,
        regime=ctx.regime,
    )
    return look, pieces, matches
