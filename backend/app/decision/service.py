from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.analytics import emitter
from app.analytics.context import context_for_option, wardrobe_count
from app.catalog.models import Option
from app.config import settings
from app.decision.models import Decision, DecisionAction, Purchase
from app.matching.models import WardrobeItem
from app.wallet.models import BudgetLedger
from app.wallet.service import current_period, get_wallet

ALLOWED_ACTIONS = {"buy", "phase", "substitute", "wait", "recreate"}


@dataclass(frozen=True)
class Evaluation:
    verdict: str
    available: float
    available_after: float
    price: float
    issues: list[dict]


def evaluate(session: Session, user_id: str, option: Option) -> Evaluation:
    wallet = get_wallet(session, user_id)
    available = float(wallet["available"])
    price = float(option.price)
    after = round(available - price, 2)
    threshold = max(settings.tight_threshold_abs, settings.tight_threshold_pct * float(wallet["base"]))
    verdict = "over" if after < 0 else "tight" if after < threshold else "fits"
    issues: list[dict] = []
    if verdict != "over":
        issues.append({"type": "buy"})
    else:
        issues.extend(
            [
                {"type": "phase", "plan": {"strategy": "stub", "months": 2}},
                {"type": "substitute", "bundle": {"strategy": "stub", "price": 92.0}},
            ]
        )
    issues.extend([{"type": "wait"}, {"type": "recreate"}])
    return Evaluation(verdict, available, after, price, issues)


def record_action(
    session: Session,
    user_id: str,
    option: Option,
    action: str,
) -> tuple[Decision, DecisionAction]:
    if action not in ALLOWED_ACTIONS:
        raise ValueError("invalid action")
    ev = evaluate(session, user_id, option)
    ctx = context_for_option(session, user_id, option)
    decision = Decision(
        user_id=user_id,
        look_id=None,
        option_id=option.id,
        verdict=ev.verdict,
        available_at=ev.available,
        price=ev.price,
    )
    session.add(decision)
    session.flush()
    row = DecisionAction(decision_id=decision.id, action=action)
    session.add(row)
    session.commit()
    emitter.emit(
        emitter.DECISION_ACTION_TAKEN,
        user_id,
        action=action,
        verdict=ev.verdict,
        capture_index=ctx.capture_index,
        wardrobe_count=ctx.wardrobe_count,
        regime=ctx.regime,
    )
    if action == "phase":
        emitter.emit(
            emitter.PLAN_CREATED,
            user_id,
            months_count=2,
            month1_total=None,
            capture_index=ctx.capture_index,
            regime=ctx.regime,
        )
    if action == "substitute":
        emitter.emit(
            emitter.SUBSTITUTION_SELECTED,
            user_id,
            bundle_price=92.0,
            delta_vs_original=round(ev.price - 92.0, 2),
            capture_index=ctx.capture_index,
            regime=ctx.regime,
        )
    return decision, row


def confirm_purchase(
    session: Session,
    user_id: str,
    option: Option,
    idempotency_key: str,
    *,
    fail_after_spend_for_test: bool = False,
) -> Purchase:
    existing = session.scalar(
        select(Purchase).where(
            Purchase.user_id == user_id,
            Purchase.idempotency_key == idempotency_key,
        )
    )
    if existing is not None:
        return existing

    ctx = context_for_option(session, user_id, option)
    before_count = ctx.wardrobe_count
    purchase = Purchase(
        user_id=user_id,
        option_id=option.id,
        price=float(option.price),
        idempotency_key=idempotency_key,
    )
    session.add(purchase)
    session.flush()

    ledger = BudgetLedger(
        user_id=user_id,
        period=current_period(),
        type="SPEND",
        amount=float(option.price),
        ref_purchase_id=purchase.id,
        idempotency_key=f"purchase:{idempotency_key}",
    )
    session.add(ledger)
    session.flush()
    if fail_after_spend_for_test:
        raise RuntimeError("forced rollback")

    from app.capture.models import LookPiece

    piece = session.get(LookPiece, option.look_piece_id)
    if piece is None:
        raise ValueError("look piece missing")
    item = WardrobeItem(
        user_id=user_id,
        category=piece.category,
        color=piece.color,
        cut=piece.cut,
        material=piece.material,
        price=float(option.price),
        source="PURCHASE",
    )
    session.add(item)
    session.flush()
    purchase.wardrobe_item_id = item.id
    session.commit()
    after_count = wardrobe_count(session, user_id)
    emitter.emit(
        emitter.PURCHASE_CONFIRMED,
        user_id,
        price=float(option.price),
        pieces_added=1,
        capture_index=ctx.capture_index,
        wardrobe_count_before=before_count,
        wardrobe_count_after=after_count,
        regime_before=ctx.regime,
    )
    emitter.emit(
        emitter.WARDROBE_ITEM_ADDED,
        user_id,
        source="PURCHASE",
        category=piece.category,
        wardrobe_count=after_count,
    )
    return purchase
