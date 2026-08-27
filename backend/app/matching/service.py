from dataclasses import dataclass

from app.capture.models import LookPiece
from app.matching.models import WardrobeItem

OWNED_THRESHOLD = 75
MIN_OWNERSHIP_EVIDENCE_WEIGHT = 65


@dataclass(frozen=True)
class MatchResult:
    wardrobe_item_id: str | None
    owned_pct: int
    is_owned: bool
    reason: str


@dataclass(frozen=True)
class SimilarityDetails:
    score: int
    reason: str
    matched_weight: int
    comparable_weight: int


def _eq(a: str | None, b: str | None) -> bool:
    return bool(a and b and a.strip().lower() == b.strip().lower())


def _comparable(a: str | None, b: str | None) -> bool:
    return bool(a and b)


def _similarity_details(piece: LookPiece, item: WardrobeItem) -> SimilarityDetails:
    if not _eq(piece.category, item.category):
        return SimilarityDetails(0, "category mismatch", 0, 0)

    checks = [
        ("category", True, 40, True),
        ("color", _eq(piece.color, item.color), 25, _comparable(piece.color, item.color)),
        ("cut", _eq(piece.cut, item.cut), 20, _comparable(piece.cut, item.cut)),
        ("material", _eq(piece.material, item.material), 15, _comparable(piece.material, item.material)),
    ]
    comparable = [(name, ok, weight) for name, ok, weight, available in checks if available]
    comparable_weight = sum(weight for _, _, weight in comparable)
    matched_weight = sum(weight for _, ok, weight in comparable if ok)
    score = round(matched_weight / comparable_weight * 100) if comparable_weight else 0

    # A normalized 100% score can be misleading when based on too little evidence.
    # Require at least 65 points of comparable evidence before ownership can cross
    # the 75% threshold: category+color qualifies, while category+cut/material alone does not.
    if comparable_weight < MIN_OWNERSHIP_EVIDENCE_WEIGHT:
        score = min(score, OWNED_THRESHOLD - 1)

    matched_names = [name for name, ok, _ in comparable if ok]
    compared_names = [name for name, _, _ in comparable]
    reason = f"matched: {', '.join(matched_names)}; compared: {', '.join(compared_names)}"
    return SimilarityDetails(score, reason, matched_weight, comparable_weight)


def similarity(piece: LookPiece, item: WardrobeItem) -> tuple[int, str]:
    details = _similarity_details(piece, item)
    return details.score, details.reason


def compute_match(piece: LookPiece, wardrobe: list[WardrobeItem]) -> MatchResult:
    if not wardrobe:
        return MatchResult(None, 0, False, "empty wardrobe")

    ranked = [(item, _similarity_details(piece, item)) for item in wardrobe]
    item, details = max(
        ranked,
        key=lambda row: (
            row[1].score >= OWNED_THRESHOLD,
            row[1].matched_weight,
            row[1].comparable_weight,
            row[1].score,
        ),
    )
    if details.score == 0:
        return MatchResult(None, 0, False, "no category match")
    return MatchResult(item.id, details.score, details.score >= OWNED_THRESHOLD, details.reason)
