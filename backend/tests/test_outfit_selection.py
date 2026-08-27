from app.capture.providers import DecomposedLook, DecomposedOutfit, DecomposedPiece
from app.capture.service import create_capture
from app.identity.deps import DEV_USER_ID
from app.identity.models import User


class SelectionCollageProvider:
    def decompose(self, image_ref: str | None = None) -> DecomposedLook:
        return DecomposedLook(
            image_type="collage",
            style="mixed",
            dominant_palette=["navy", "beige"],
            outfits=[
                DecomposedOutfit(
                    style="look zero",
                    pieces=[DecomposedPiece("shirt", "shirt", "white", None, None, None, 0.9)],
                ),
                DecomposedOutfit(
                    style="look one",
                    pieces=[
                        DecomposedPiece("pants", "trousers", "beige", None, None, None, 0.9),
                        DecomposedPiece("polo shirt", "polo", "navy", None, None, None, 0.9),
                    ],
                ),
            ],
            representative_outfit_index=0,
        )


def _ensure_user(session) -> None:
    if session.get(User, DEV_USER_ID) is None:
        session.add(User(id=DEV_USER_ID, auth_ref="dev", region="EU"))
        session.commit()


def test_selecting_outfit_persists_and_changes_representative_pieces(client, session) -> None:
    _ensure_user(session)
    _, look = create_capture(session, DEV_USER_ID, SelectionCollageProvider(), "object-key")
    initial = client.get(f"/looks/{look.id}").json()
    second = initial["outfits"][1]

    response = client.post(f"/looks/{look.id}/selection", json={"outfit_id": second["id"]})
    assert response.status_code == 200
    assert response.json()["representative_outfit_index"] == 1

    refreshed = client.get(f"/looks/{look.id}").json()
    assert refreshed["representative_outfit_index"] == 1
    assert refreshed["outfits"][0]["is_representative"] is False
    assert refreshed["outfits"][1]["is_representative"] is True
    assert {piece["id"] for piece in refreshed["pieces"]} == {piece["id"] for piece in second["pieces"]}

    missing = client.get(f"/looks/{look.id}/gaps").json()["missing"]
    assert set(missing) == {piece["id"] for piece in second["pieces"]}


def test_selection_rejects_outfit_from_another_look(client, session) -> None:
    _ensure_user(session)
    _, first = create_capture(session, DEV_USER_ID, SelectionCollageProvider(), "first")
    _, second = create_capture(session, DEV_USER_ID, SelectionCollageProvider(), "second")
    foreign_outfit = client.get(f"/looks/{second.id}").json()["outfits"][1]

    response = client.post(f"/looks/{first.id}/selection", json={"outfit_id": foreign_outfit["id"]})
    assert response.status_code == 404
    assert response.json()["detail"] == "outfit not found"
