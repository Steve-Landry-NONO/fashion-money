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


def _comparable(a: str | None, b: str | None) -> bool:
    return bool(a and b)


def similarity(piece: LookPiece, item: WardrobeItem) -> tuple[int, str]:
    if not _eq(piece.category, item.category):
        return 0, "category mismatch"

    checks = [
        ("category", True, 40, True),
        ("color", _eq(piece.color, item.color), 25, _comparable(piece.color, item.color)),
        ("cut", _eq(piece.cut, item.cut), 20, _comparable(piece.cut, item.cut)),
        ("material", _eq(piece.material, item.material), 15, _comparable(piece.material, item.material)),
    ]
    comparable = [(name, ok, weight) for name, ok, weight, available in checks if available]
    denominator = sum(weight for _, _, weight in comparable)
    matched = sum(weight for _, ok, weight in comparable if ok)

    # Category alone is not enough evidence to claim ownership. This matters for sparse
    # manually-entered wardrobe items and conservative Vision outputs with null attributes.
    has_non_category_evidence = any(name != "category" for name, _, _ in comparable)
    score = round(matched / denominator * 100) if denominator else 0
    if not has_non_category_evidence:
        score = min(score, OWNED_THRESHOLD - 1)

    matched_names = [name for name, ok, _ in comparable if ok]
    compared_names = [name for name, _, _ in comparable]
    reason = f"matched: {', '.join(matched_names)}; compared: {', '.join(compared_names)}"
    return score, reason


def compute_match(piece: LookPiece, wardrobe: list[WardrobeItem]) -> MatchResult:
    if not wardrobe:
        return MatchResult(None, 0, False, "empty wardrobe")
    ranked = [(item, *similarity(piece, item)) for item in wardrobe]
    item, score, reason = max(ranked, key=lambda row: row[1])
    if score == 0:
        return MatchResult(None, 0, False, "no category match")
    return MatchResult(item.id, score, score >= OWNED_THRESHOLD, reason)
