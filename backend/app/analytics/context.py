from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.capture.models import Capture, Look, LookPiece
from app.catalog.models import Option
from app.matching.models import WardrobeItem


@dataclass(frozen=True)
class AnalyticsContext:
    capture_index: int | None
    wardrobe_count: int
    regime: str


def wardrobe_count(session: Session, user_id: str) -> int:
    return int(
        session.scalar(
            select(func.count()).select_from(WardrobeItem).where(WardrobeItem.user_id == user_id)
        )
        or 0
    )


def regime_for_wardrobe(count: int) -> str:
    return "j0" if count == 0 else "mature"


def context_for_capture(session: Session, user_id: str, capture: Capture) -> AnalyticsContext:
    count = wardrobe_count(session, user_id)
    capture_index = int(
        session.scalar(
            select(func.count())
            .select_from(Capture)
            .where(
                Capture.user_id == user_id,
                Capture.created_at <= capture.created_at,
            )
        )
        or 1
    )
    return AnalyticsContext(
        capture_index=capture_index,
        wardrobe_count=count,
        regime=regime_for_wardrobe(count),
    )


def context_for_option(session: Session, user_id: str, option: Option) -> AnalyticsContext:
    piece = session.get(LookPiece, option.look_piece_id)
    look = session.get(Look, piece.look_id) if piece else None
    capture = session.get(Capture, look.capture_id) if look else None
    if capture is None or capture.user_id != user_id:
        count = wardrobe_count(session, user_id)
        return AnalyticsContext(None, count, regime_for_wardrobe(count))
    return context_for_capture(session, user_id, capture)
