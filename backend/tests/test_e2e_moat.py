from sqlalchemy import func, select

from app.decision.models import Decision, DecisionAction, Purchase
from app.identity.deps import DEV_USER_ID
from app.matching.models import WardrobeItem
from app.wallet.models import BudgetLedger


def _setup_look(client):
    assert client.post("/budget", json={"base_amount": 100}).status_code == 200
    cap = client.post("/captures", json={}).json()
    look = client.get(f"/looks/{cap['look_id']}").json()
    return cap, look


def test_j0_capture_is_zero_match_and_has_four_gaps(client):
    cap, look = _setup_look(client)
    assert look["score_look"] == 0
    assert all(p["owned_pct"] == 0 for p in look["pieces"])
    gaps = client.get(f"/looks/{cap['look_id']}/gaps").json()
    assert len(gaps["missing"]) == 4


def test_mature_matching_reduces_gap_and_is_debuggable(client):
    client.post("/budget", json={"base_amount": 100})
    for item in [
        {"category": "t-shirt", "color": "white", "cut": "regular", "material": "cotton"},
        {"category": "trousers", "color": "black", "cut": "straight", "material": "cotton"},
        {"category": "sneakers", "color": "white", "cut": "low-top", "material": "leather"},
    ]:
        assert client.post("/wardrobe/items", json=item).status_code == 201
    cap = client.post("/captures", json={}).json()
    look = client.get(f"/looks/{cap['look_id']}").json()
    assert look["score_look"] == 75
    owned = [p for p in look["pieces"] if p["is_owned"]]
    assert len(owned) == 3
    assert all(p["match_reason"] for p in owned)
    gaps = client.get(f"/looks/{cap['look_id']}/gaps").json()
    assert len(gaps["missing"]) == 1


def test_mock_options_and_best_are_score_driven(client):
    cap, _ = _setup_look(client)
    client.get(f"/looks/{cap['look_id']}")
    piece_id = client.get(f"/looks/{cap['look_id']}/gaps").json()["missing"][0]
    options = client.get(f"/gaps/{piece_id}/options").json()["options"]
    assert [o["price"] for o in options] == [39.99, 49.99, 69.99]
    best = [o for o in options if o["is_best"]]
    assert len(best) == 1
    assert best[0]["price"] == 49.99


def test_decision_evaluate_is_financially_side_effect_free(client, session):
    cap, _ = _setup_look(client)
    client.get(f"/looks/{cap['look_id']}")
    piece_id = client.get(f"/looks/{cap['look_id']}/gaps").json()["missing"][0]
    option = client.get(f"/gaps/{piece_id}/options").json()["options"][1]
    before_ledger = session.scalar(select(func.count()).select_from(BudgetLedger))
    before_decisions = session.scalar(select(func.count()).select_from(Decision))
    ev = client.post("/decisions/evaluate", json={"option_id": option["id"]})
    assert ev.status_code == 200
    assert ev.json()["verdict"] == "fits"
    assert ev.json()["available_after"] == 50.01
    assert session.scalar(select(func.count()).select_from(BudgetLedger)) == before_ledger
    assert session.scalar(select(func.count()).select_from(Decision)) == before_decisions


def test_server_records_activation_action(client, session):
    cap, _ = _setup_look(client)
    client.get(f"/looks/{cap['look_id']}")
    piece_id = client.get(f"/looks/{cap['look_id']}/gaps").json()["missing"][0]
    option = client.get(f"/gaps/{piece_id}/options").json()["options"][1]
    r = client.post("/decisions/actions", json={"option_id": option["id"], "action": "buy"})
    assert r.status_code == 201
    assert session.scalar(select(func.count()).select_from(DecisionAction)) == 1


def test_purchase_confirmation_updates_wallet_and_wardrobe_once(client, session):
    cap, _ = _setup_look(client)
    client.get(f"/looks/{cap['look_id']}")
    piece_id = client.get(f"/looks/{cap['look_id']}/gaps").json()["missing"][0]
    option = client.get(f"/gaps/{piece_id}/options").json()["options"][1]
    payload = {"option_id": option["id"], "idempotency_key": "demo-purchase-1"}
    first = client.post("/purchases/confirm", json=payload)
    second = client.post("/purchases/confirm", json=payload)
    assert first.status_code == 200 and second.status_code == 200
    assert first.json()["purchase_id"] == second.json()["purchase_id"]
    assert first.json()["wallet"]["available"] == 50.01
    assert session.scalar(select(func.count()).select_from(Purchase)) == 1
    wardrobe_count = session.scalar(
        select(func.count()).select_from(WardrobeItem).where(WardrobeItem.user_id == DEV_USER_ID)
    )
    assert wardrobe_count == 1
    spend_count = session.scalar(
        select(func.count()).select_from(BudgetLedger).where(BudgetLedger.type == "SPEND")
    )
    assert spend_count == 1
