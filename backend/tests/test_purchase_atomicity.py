from sqlalchemy import func, select

from app.catalog.models import Option
from app.decision import service
from app.decision.models import Purchase
from app.identity.deps import DEV_USER_ID
from app.matching.models import WardrobeItem
from app.wallet.models import BudgetLedger


def test_purchase_rolls_back_all_mutations_on_failure(client, session):
    client.post("/budget", json={"base_amount": 100})
    cap = client.post("/captures", json={}).json()
    client.get(f"/looks/{cap['look_id']}")
    piece_id = client.get(f"/looks/{cap['look_id']}/gaps").json()["missing"][0]
    option_id = client.get(f"/gaps/{piece_id}/options").json()["options"][1]["id"]
    option = session.get(Option, option_id)
    assert option is not None
    try:
        service.confirm_purchase(session, DEV_USER_ID, option, "rollback-1", fail_after_spend_for_test=True)
    except RuntimeError:
        session.rollback()
    else:
        raise AssertionError("expected forced failure")
    assert session.scalar(select(func.count()).select_from(Purchase)) == 0
    assert session.scalar(select(func.count()).select_from(BudgetLedger).where(BudgetLedger.type == "SPEND")) == 0
    assert session.scalar(select(func.count()).select_from(WardrobeItem)) == 0
