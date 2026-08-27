from sqlalchemy import select

from app.capture.models import LookOutfit, LookPiece
from app.capture.providers import (
    DecomposedLook,
    DecomposedOutfit,
    DecomposedPiece,
    VisionLook,
    _to_decomposed_look,
    normalize_category,
)
from app.capture.service import create_capture
from app.identity.models import User


def test_normalize_category_aliases() -> None:
    assert normalize_category("Pants") == "trousers"
    assert normalize_category("polo shirt") == "polo"
    assert normalize_category("Loafers") == "shoes"
    assert normalize_category("cardigan") == "cardigan"


def test_to_decomposed_look_filters_empty_and_avoids_one_piece_representative() -> None:
    parsed = VisionLook.model_validate(
        {
            "image_type": "single_outfit",
            "style": "smart casual",
            "dominant_palette": ["navy", "beige"],
            "representative_outfit_index": 0,
            "outfits": [
                {
                    "style": "ghost",
                    "pieces": [
                        {
                            "category": "t-shirt",
                            "color": "black",
                            "cut": None,
                            "material": None,
                            "swatch": None,
                            "confidence": 0.8,
                        }
                    ],
                },
                {"style": "empty", "pieces": []},
                {
                    "style": "smart casual",
                    "pieces": [
                        {
                            "category": "pants",
                            "color": "beige",
                            "cut": "wide leg",
                            "material": None,
                            "swatch": None,
                            "confidence": 0.9,
                        },
                        {
                            "category": "polo shirt",
                            "color": "navy",
                            "cut": "short sleeve",
                            "material": None,
                            "swatch": None,
                            "confidence": 0.9,
                        },
                    ],
                },
            ],
        }
    )

    look = _to_decomposed_look(parsed)

    assert look.image_type == "collage"
    assert len(look.outfits) == 2
    assert look.representative_outfit_index == 1
    assert [piece.category for piece in look.pieces] == ["trousers", "polo"]
    assert look.pieces[0].category_raw == "pants"


class TwoOutfitProvider:
    def decompose(self, image_ref: str | None = None) -> DecomposedLook:
        return DecomposedLook(
            image_type="collage",
            style="minimalist",
            dominant_palette=["black", "beige"],
            outfits=[
                DecomposedOutfit(
                    style="look one",
                    pieces=[
                        DecomposedPiece("pants", "trousers", "beige", "wide leg", None, None, 0.91),
                        DecomposedPiece("shirt", "shirt", "black", "regular", None, None, 0.88),
                    ],
                ),
                DecomposedOutfit(
                    style="look two",
                    pieces=[DecomposedPiece("polo shirt", "polo", "navy", "regular", None, None, 0.84)],
                ),
            ],
            representative_outfit_index=0,
        )


def test_create_capture_persists_all_outfits_raw_category_and_confidence(session) -> None:
    user = User(auth_ref="vision-contract-test")
    session.add(user)
    session.commit()

    _, look = create_capture(session, user.id, TwoOutfitProvider(), "object-key")

    outfits = list(
        session.scalars(select(LookOutfit).where(LookOutfit.look_id == look.id).order_by(LookOutfit.position)).all()
    )
    pieces = list(session.scalars(select(LookPiece).where(LookPiece.look_id == look.id)).all())

    assert look.image_type == "collage"
    assert look.dominant_palette == ["black", "beige"]
    assert look.representative_outfit_index == 0
    assert len(outfits) == 2
    assert [outfit.is_representative for outfit in outfits] == [True, False]
    assert len(pieces) == 3
    assert {piece.category_raw for piece in pieces} == {"pants", "shirt", "polo shirt"}
    assert {piece.confidence for piece in pieces} == {0.91, 0.88, 0.84}
    assert all(piece.outfit_id is not None for piece in pieces)
