"""VS-04/05 — wallet API + derived balance, over SQLite."""
from app.identity.deps import DEV_USER_ID
from app.wallet import service


def test_set_budget_then_wallet(client):
    r = client.post("/budget", json={"base_amount": 100})
    assert r.status_code == 200
    body = r.json()
    assert body["base"] == 100.0
    assert body["available"] == 100.0
    assert body["spent"] == 0.0


def test_wallet_reflects_ledger_derivation(client, session):
    client.post("/budget", json={"base_amount": 100})
    # simulate the v0.2 scenario: already spent 20, then a 49.99 purchase
    service.add_entry(session, DEV_USER_ID, "SPEND", 20.0)
    service.add_entry(session, DEV_USER_ID, "SPEND", 49.99)
    r = client.get("/wallet")
    body = r.json()
    assert body["spent"] == 69.99
    assert body["available"] == 30.01  # <- matches prototype v0.2


def test_wallet_404_when_no_budget(client):
    assert client.get("/wallet").status_code == 404


def test_idempotency_key_blocks_double_spend(client, session):
    client.post("/budget", json={"base_amount": 100})
    service.add_entry(session, DEV_USER_ID, "SPEND", 49.99, idempotency_key="p-1")
    try:
        service.add_entry(session, DEV_USER_ID, "SPEND", 49.99, idempotency_key="p-1")
    except Exception:
        session.rollback()
    else:
        raise AssertionError("expected uniqueness violation on duplicate idempotency_key")
    r = client.get("/wallet")
    assert r.json()["spent"] == 49.99  # counted once
