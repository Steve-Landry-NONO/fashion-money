"""Analytics emitter (VS-15). Schema is OURS; collection infra is bought.

Dev sink = stdout; prod sink = SaaS. Activation is defined server-side:
`capture_started` -> `decision_action_taken` (see decision router / refinement 4).
"""
import json
import sys

from app.config import settings

# Event names mirror PRD §7.
BUDGET_SET = "budget_set"
CAPTURE_STARTED = "capture_started"
LOOK_DECOMPOSED = "look_decomposed"
MATCH_COMPUTED = "match_computed"
GAP_IDENTIFIED = "gap_identified"
OPTIONS_VIEWED = "options_viewed"
OPTION_SELECTED = "option_selected"
DECISION_VIEWED = "decision_viewed"
DECISION_ACTION_TAKEN = "decision_action_taken"
PLAN_CREATED = "plan_created"
SUBSTITUTION_SELECTED = "substitution_selected"
PURCHASE_CONFIRMED = "purchase_confirmed"
WARDROBE_ITEM_ADDED = "wardrobe_item_added"
RETURN_SESSION = "return_session"


def emit(event: str, user_id: str, **props: object) -> None:
    payload = {"event": event, "user_id": user_id, "props": props}
    if settings.analytics_sink == "stdout":
        print(json.dumps(payload), file=sys.stdout, flush=True)
    else:  # pragma: no cover - wired to SaaS in prod
        raise NotImplementedError("SaaS analytics sink not configured")
