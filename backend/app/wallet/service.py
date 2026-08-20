from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.analytics import emitter
from app.config import settings
from app.wallet import ledger_math as lm
from app.wallet.models import BudgetConfig, BudgetLedger


def current_period(now: datetime | None = None) -> str:
    now = now or datetime.now(UTC)
    return f"{now.year:04d}-{now.month:02d}"


def set_budget(
    session: Session,
    user_id: str,
    base_amount: float,
    rollover_cap: float | None,
) -> BudgetConfig:
    cap = rollover_cap if rollover_cap is not None else settings.rollover_cap_multiplier * base_amount
    cfg = session.get(BudgetConfig, user_id)
    if cfg is None:
        cfg = BudgetConfig(user_id=user_id, base_amount=base_amount, rollover_cap=cap)
        session.add(cfg)
    else:
        cfg.base_amount = base_amount
        cfg.rollover_cap = cap
    session.commit()
    emitter.emit(emitter.BUDGET_SET, user_id, base_amount=base_amount, rollover_cap=cap)
    return cfg


def _period_entries(session: Session, user_id: str, period: str) -> list[tuple[str, float]]:
    rows = session.execute(
        select(BudgetLedger.type, BudgetLedger.amount).where(
            BudgetLedger.user_id == user_id,
            BudgetLedger.period == period,
        )
    ).all()
    return [(t, float(a)) for t, a in rows]


def get_wallet(session: Session, user_id: str) -> dict:
    cfg = session.get(BudgetConfig, user_id)
    if cfg is None:
        raise ValueError("budget not set")
    period = current_period()
    entries = _period_entries(session, user_id, period)
    base = float(cfg.base_amount)
    available = lm.compute_available(base, entries)
    spent = round(sum(a for t, a in entries if t == lm.SPEND), 2)
    rollover_in = round(sum(a for t, a in entries if t == lm.ROLLOVER_IN), 2)
    return {
        "period": period,
        "base": base,
        "rollover_in": rollover_in,
        "spent": spent,
        "available": available,
    }


def add_entry(
    session: Session,
    user_id: str,
    etype: str,
    amount: float,
    *,
    period: str | None = None,
    idempotency_key: str | None = None,
    ref_purchase_id: str | None = None,
) -> BudgetLedger:
    """Append a ledger row. Idempotency and rollover uniqueness are DB-enforced."""
    entry = BudgetLedger(
        user_id=user_id,
        period=period or current_period(),
        type=etype,
        amount=amount,
        idempotency_key=idempotency_key,
        ref_purchase_id=ref_purchase_id,
    )
    session.add(entry)
    session.commit()
    return entry


def apply_rollover(session: Session, user_id: str, from_period: str, to_period: str) -> BudgetLedger:
    """Credit unused budget from one calendar month into the next.

    This is the deterministic primitive used by the monthly job. Re-running it
    returns the existing rollover row and never credits the user twice.
    """
    cfg = session.get(BudgetConfig, user_id)
    if cfg is None:
        raise ValueError("budget not set")

    existing = session.scalar(
        select(BudgetLedger).where(
            BudgetLedger.user_id == user_id,
            BudgetLedger.period == to_period,
            BudgetLedger.type == lm.ROLLOVER_IN,
        )
    )
    if existing is not None:
        return existing

    previous_entries = _period_entries(session, user_id, from_period)
    previous_available = lm.compute_available(float(cfg.base_amount), previous_entries)
    amount = round(min(max(previous_available, 0.0), float(cfg.rollover_cap)), 2)

    rollover = BudgetLedger(
        user_id=user_id,
        period=to_period,
        type=lm.ROLLOVER_IN,
        amount=amount,
        idempotency_key=f"rollover:{to_period}",
    )
    session.add(rollover)
    session.commit()
    return rollover
