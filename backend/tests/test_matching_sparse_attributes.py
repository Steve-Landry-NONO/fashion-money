from app.capture.models import LookPiece
from app.matching.models import WardrobeItem
from app.matching.service import OWNED_THRESHOLD, compute_match, similarity


def test_category_and_color_can_match_when_other_attributes_are_unknown() -> None:
    piece = LookPiece(category="trousers", color="beige", cut=None, material=None)
    item = WardrobeItem(user_id="u", category="trousers", color="beige", cut=None, material=None, source="manual")

    score, reason = similarity(piece, item)

    assert score == 100
    assert score >= OWNED_THRESHOLD
    assert "color" in reason


def test_unknown_attribute_is_not_counted_as_a_mismatch() -> None:
    piece = LookPiece(category="trousers", color="beige", cut="wide leg", material=None)
    item = WardrobeItem(user_id="u", category="trousers", color="beige", cut=None, material=None, source="manual")

    score, _ = similarity(piece, item)

    assert score == 100


def test_category_only_is_not_enough_to_claim_ownership() -> None:
    piece = LookPiece(category="shirt", color=None, cut=None, material=None)
    item = WardrobeItem(user_id="u", category="shirt", color=None, cut=None, material=None, source="manual")

    score, _ = similarity(piece, item)

    assert score < OWNED_THRESHOLD


def test_category_plus_cut_only_is_not_enough_to_claim_ownership() -> None:
    piece = LookPiece(category="trousers", color=None, cut="straight", material=None)
    item = WardrobeItem(user_id="u", category="trousers", color="red", cut="straight", material=None, source="manual")

    score, _ = similarity(piece, item)

    assert score < OWNED_THRESHOLD


def test_comparable_color_mismatch_keeps_score_below_owned_threshold() -> None:
    piece = LookPiece(category="trousers", color="beige", cut=None, material=None)
    item = WardrobeItem(user_id="u", category="trousers", color="black", cut=None, material=None, source="manual")

    score, _ = similarity(piece, item)

    assert score < OWNED_THRESHOLD


def test_ranking_prefers_richer_evidence_when_matched_weight_is_equal() -> None:
    piece = LookPiece(category="trousers", color="beige", cut="wide leg", material=None)
    precise = WardrobeItem(
        id="precise",
        user_id="u",
        category="trousers",
        color="beige",
        cut="straight",
        material="linen",
        source="manual",
    )
    vague = WardrobeItem(
        id="vague",
        user_id="u",
        category="trousers",
        color="beige",
        cut=None,
        material=None,
        source="manual",
    )

    result = compute_match(piece, [vague, precise])

    assert result.is_owned is True
    assert result.wardrobe_item_id == "precise"
    assert "cut" in result.reason
