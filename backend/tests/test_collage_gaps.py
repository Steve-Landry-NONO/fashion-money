"""Collage looks: gaps and matches must be scoped to one outfit, never the union."""

from app.capture.providers import DecomposedLook, DecomposedOutfit, DecomposedPiece
from app.capture.service import create_capture
from app.identity.deps import DEV_USER_ID
from app.identity.models import User
from app.matching.models import WardrobeItem


class FourOutfitCollageProvider:
    def decompose(self, image_ref: str | None = None) -> DecomposedLook:
        def outfit(tag: str) -> DecomposedOutfit:
            return DecomposedOutfit(
                style=tag,
                pieces=[
                    DecomposedPiece("pants", "trousers", "beige", "wide leg", "cotton", None, 0.9),
                    DecomposedPiece("shirt", "shirt", "black", None, None, None, 0.9),
                    DecomposedPiece("sneaker", "sneakers", "white", None, None, None, 0.9),
                ],
            )

        return DecomposedLook(
            image_type="collage",
            style="collage",
            dominant_palette=["beige", "black"],
            outfits=[outfit(f"look {index}") for index in range(4)],
            representative_outfit_index=0,
        )


def _dev_user(session) -> User:
    user = session.get(User, DEV_USER_ID)
    if user is None:
        user = User(id=DEV_USER_ID, auth_ref="dev", region="EU")
        session.add(user)
        session.commit()
    return user


def test_gaps_are_scoped_to_the_representative_outfit(client, session) -> None:
    _dev_user(session)
    _, look = create_capture(session, DEV_USER_ID, FourOutfitCollageProvider(), "object-key")

    body = client.get(f"/looks/{look.id}").json()
    assert len(body["outfits"]) == 4
    assert len(body["pieces"]) == 3

    missing = client.get(f"/looks/{look.id}/gaps").json()["missing"]
    assert len(missing) == 3


def test_gaps_can_target_a_selected_outfit(client, session) -> None:
    _dev_user(session)
    _, look = create_capture(session, DEV_USER_ID, FourOutfitCollageProvider(), "object-key")

    body = client.get(f"/looks/{look.id}").json()
    second = body["outfits"][1]
    assert second["is_representative"] is False

    missing = client.get(f"/looks/{look.id}/gaps", params={"outfit_id": second["id"]}).json()["missing"]
    assert len(missing) == 3
    assert set(missing) == {piece["id"] for piece in second["pieces"]}


def test_unknown_outfit_id_is_rejected(client, session) -> None:
    _dev_user(session)
    _, look = create_capture(session, DEV_USER_ID, FourOutfitCollageProvider(), "object-key")

    assert client.get(f"/looks/{look.id}/gaps", params={"outfit_id": "nope"}).status_code == 404


def test_non_representative_outfits_report_real_ownership(client, session) -> None:
    user = _dev_user(session)
    session.add(
        WardrobeItem(
            user_id=user.id,
            category="trousers",
            color="beige",
            cut="wide leg",
            material="cotton",
            source="manual",
        )
    )
    session.commit()

    _, look = create_capture(session, DEV_USER_ID, FourOutfitCollageProvider(), "object-key")
    body = client.get(f"/looks/{look.id}").json()

    for outfit in body["outfits"]:
        owned = [piece for piece in outfit["pieces"] if piece["is_owned"]]
        assert owned, f"outfit {outfit['position']} reports 0 owned despite matching trousers"
        assert all(piece["match_reason"] for piece in outfit["pieces"])
