from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.capture import service
from app.capture.providers import get_decomposition_provider
from app.capture.schemas import CaptureIn, CaptureOut, LookOut, OutfitOut, PieceOut
from app.capture.storage import ALLOWED_IMAGE_TYPES, get_image_storage
from app.config import settings
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
    """Legacy/mock JSON entry point kept for deterministic tests."""
    capture, look = service.create_capture(session, user.id, get_decomposition_provider(), body.image_ref)
    return CaptureOut(capture_id=capture.id, look_id=look.id, status=capture.status)


@router.post("/captures/upload", response_model=CaptureOut, status_code=201)
async def upload_capture(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> CaptureOut:
    content_type = (file.content_type or "").lower()
    if content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(status_code=415, detail="supported formats: JPEG, PNG, WEBP")
    data = await file.read(settings.max_image_bytes + 1)
    if not data:
        raise HTTPException(status_code=422, detail="empty image")
    if len(data) > settings.max_image_bytes:
        raise HTTPException(status_code=413, detail="image exceeds size limit")

    storage = get_image_storage()
    object_key = storage.put(user.id, data, content_type)
    try:
        provider = get_decomposition_provider(storage)
        capture, look = service.create_capture(session, user.id, provider, object_key)
    except (RuntimeError, ValueError) as exc:
        session.rollback()
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return CaptureOut(capture_id=capture.id, look_id=look.id, status=capture.status)


def _piece_out(piece, match=None) -> PieceOut:
    return PieceOut(
        id=piece.id,
        category_raw=piece.category_raw,
        category=piece.category,
        color=piece.color,
        cut=piece.cut,
        material=piece.material,
        swatch=piece.swatch,
        confidence=piece.confidence,
        owned_pct=match.owned_pct if match else 0,
        is_owned=match.is_owned if match else False,
        match_reason=match.reason if match else None,
    )


@router.get("/looks/{look_id}", response_model=LookOut)
def get_look(look_id: str, user: User = Depends(get_current_user), session: Session = Depends(get_session)) -> LookOut:
    try:
        look, outfits, all_pieces, matches = service.get_look_for_user(session, user.id, look_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="look not found") from None

    by_piece = {match.look_piece_id: match for match in matches}
    representative_ids = {outfit.id for outfit in outfits if outfit.is_representative}
    representative_pieces = [piece for piece in all_pieces if piece.outfit_id in representative_ids]
    if not representative_ids:
        representative_pieces = all_pieces

    pieces_out = [_piece_out(piece, by_piece.get(piece.id)) for piece in representative_pieces]
    score = round(sum(1 for piece in pieces_out if piece.is_owned) / len(pieces_out) * 100) if pieces_out else 0

    outfit_outputs = []
    for outfit in outfits:
        outfit_pieces = [piece for piece in all_pieces if piece.outfit_id == outfit.id]
        outfit_outputs.append(
            OutfitOut(
                id=outfit.id,
                position=outfit.position,
                style=outfit.style,
                is_representative=outfit.is_representative,
                pieces=[_piece_out(piece, by_piece.get(piece.id)) for piece in outfit_pieces],
            )
        )

    return LookOut(
        id=look.id,
        style=look.style,
        image_type=look.image_type,
        dominant_palette=look.dominant_palette,
        representative_outfit_index=look.representative_outfit_index,
        outfits=outfit_outputs,
        pieces=pieces_out,
        score_look=score,
    )
