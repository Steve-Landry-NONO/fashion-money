from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.analytics import emitter
from app.analytics.context import context_for_capture
from app.capture.models import Capture, Look, LookOutfit, LookPiece
from app.capture.providers import DecompositionProvider
from app.matching.models import Match, WardrobeItem
from app.matching.service import compute_match


def pieces_for_outfit(
    outfits: list[LookOutfit],
    all_pieces: list[LookPiece],
    outfit_id: str | None = None,
) -> list[LookPiece]:
    """Return pieces for the selected outfit, defaulting to the representative one."""
    if outfit_id is not None:
        return [piece for piece in all_pieces if piece.outfit_id == outfit_id]
    representative_ids = {outfit.id for outfit in outfits if outfit.is_representative}
    if not representative_ids:
        return all_pieces
    return [piece for piece in all_pieces if piece.outfit_id in representative_ids]


def select_outfit(session: Session, user_id: str, look_id: str, outfit_id: str) -> LookOutfit:
    """Make one persisted outfit the active/representative look for the user."""
    look = session.get(Look, look_id)
    if look is None:
        raise ValueError("look not found")
    capture = session.get(Capture, look.capture_id)
    if capture is None or capture.user_id != user_id:
        raise ValueError("look not found")

    outfits = list(
        session.scalars(select(LookOutfit).where(LookOutfit.look_id == look_id).order_by(LookOutfit.position)).all()
    )
    selected = next((outfit for outfit in outfits if outfit.id == outfit_id), None)
    if selected is None:
        raise ValueError("outfit not found")

    for outfit in outfits:
        outfit.is_representative = outfit.id == selected.id
    look.representative_outfit_index = selected.position
    session.commit()
    session.refresh(selected)
    return selected


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
    look = Look(
        capture_id=capture.id,
        style=decomposed.style,
        image_type=decomposed.image_type,
        dominant_palette=decomposed.dominant_palette,
        representative_outfit_index=decomposed.representative_outfit_index,
    )
    session.add(look)
    session.flush()

    for position, outfit in enumerate(decomposed.outfits):
        outfit_row = LookOutfit(
            look_id=look.id,
            position=position,
            style=outfit.style,
            is_representative=position == decomposed.representative_outfit_index,
        )
        session.add(outfit_row)
        session.flush()
        for piece in outfit.pieces:
            session.add(
                LookPiece(
                    look_id=look.id,
                    outfit_id=outfit_row.id,
                    category_raw=piece.category_raw,
                    category=piece.category,
                    color=piece.color,
                    cut=piece.cut,
                    material=piece.material,
                    swatch=piece.swatch,
                    confidence=piece.confidence,
                )
            )

    capture.status = "ready"
    session.commit()
    emitter.emit(
        emitter.LOOK_DECOMPOSED,
        user_id,
        pieces_count=len(decomposed.pieces),
        outfits_count=len(decomposed.outfits),
        image_type=decomposed.image_type,
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
) -> tuple[Look, list[LookOutfit], list[LookPiece], list[Match]]:
    look = session.get(Look, look_id)
    if look is None:
        raise ValueError("look not found")
    capture = session.get(Capture, look.capture_id)
    if capture is None or capture.user_id != user_id:
        raise ValueError("look not found")

    outfits = list(
        session.scalars(select(LookOutfit).where(LookOutfit.look_id == look_id).order_by(LookOutfit.position)).all()
    )
    all_pieces = list(session.scalars(select(LookPiece).where(LookPiece.look_id == look_id)).all())
    pieces = pieces_for_outfit(outfits, all_pieces)

    wardrobe = list(session.scalars(select(WardrobeItem).where(WardrobeItem.user_id == user_id)).all())
    piece_ids = [piece.id for piece in all_pieces]
    if piece_ids:
        session.execute(delete(Match).where(Match.look_piece_id.in_(piece_ids)))

    matches: list[Match] = []
    for piece in all_pieces:
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

    scored_ids = {piece.id for piece in pieces}
    owned = sum(1 for match in matches if match.look_piece_id in scored_ids and match.is_owned)
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
    return look, outfits, all_pieces, matches
