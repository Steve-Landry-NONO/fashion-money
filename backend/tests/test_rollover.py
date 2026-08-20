from sqlalchemy import func, select

from app.identity.models import User
from app.wallet.models import BudgetLedger
from app.wallet.service import add_entry, apply_rollover, set_budget


def _user(session) -> User:
    user = User(auth_ref="rollover-test")
    session.add(user)
    session.commit()
    return user


def test_rollover_carries_unused_budget_up_to_cap(session):
    user = _user(session)
    set_budget(session, user.id, base_amount=100.0, rollover_cap=60.0)
    add_entry(session, user.id, "SPEND", 25.0, period="2026-08")

    row = apply_rollover(session, user.id, "2026-08", "2026-09")

    assert float(row.amount) == 60.0
    assert row.period == "2026-09"
    assert row.type == "ROLLOVER_IN"


def test_rollover_is_idempotent(session):
    user = _user(session)
    set_budget(session, user.id, base_amount=100.0, rollover_cap=100.0)
    add_entry(session, user.id, "SPEND", 20.0, period="2026-08")

    first = apply_rollover(session, user.id, "2026-08", "2026-09")
    second = apply_rollover(session, user.id, "2026-08", "2026-09")

    assert first.id == second.id
    count = session.scalar(
        select(func.count()).select_from(BudgetLedger).where(
            BudgetLedger.user_id == user.id,
            BudgetLedger.period == "2026-09",
            BudgetLedger.type == "ROLLOVER_IN",
        )
    )
    assert count == 1


def test_negative_previous_available_rolls_zero(session):
    user = _user(session)
    set_budget(session, user.id, base_amount=100.0, rollover_cap=100.0)
    add_entry(session, user.id, "SPEND", 120.0, period="2026-08")

    row = apply_rollover(session, user.id, "2026-08", "2026-09")

    assert float(row.amount) == 0.0
