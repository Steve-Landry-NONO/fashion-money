from dataclasses import dataclass

from app.capture.models import LookPiece
from app.matching.models import WardrobeItem

OWNED_THRESHOLD = 75


@dataclass(frozen=True)
class MatchResult:
    wardrobe_item_id: str | None
    owned_pct: int
    is_owned: bool
    reason: str


def _eq(a: str | None, b: str | None) -> bool:
    return bool(a and b and a.strip().lower() == b.strip().lower())


def similarity(piece: LookPiece, item: WardrobeItem) -> tuple[int, str]:
    if not _eq(piece.category, item.category):
        return 0, "category mismatch"
    checks = [
        ("category", True, 40),
        ("color", _eq(piece.color, item.color), 25),
        ("cut", _eq(piece.cut, item.cut), 20),
        ("material", _eq(piece.material, item.material), 15),
    ]
    score = sum(weight for _, ok, weight in checks if ok)
    reason = ", ".join(name for name, ok, _ in checks if ok)
    return score, reason


def compute_match(piece: LookPiece, wardrobe: list[WardrobeItem]) -> MatchResult:
    if not wardrobe:
        return MatchResult(None, 0, False, "empty wardrobe")
    ranked = [(item, *similarity(piece, item)) for item in wardrobe]
    item, score, reason = max(ranked, key=lambda row: row[1])
    if score == 0:
        return MatchResult(None, 0, False, "no category match")
    return MatchResult(item.id, score, score >= OWNED_THRESHOLD, reason)
