"""VS-05 unit tests — pure derivation, no DB required."""
from app.wallet.ledger_math import (
    ADJUST,
    ROLLOVER_IN,
    SPEND,
    compute_available,
    compute_rollover,
)


def test_empty_ledger_equals_base():
    assert compute_available(100.0, []) == 100.0


def test_spend_decrements():
    assert compute_available(100.0, [(SPEND, 20.0)]) == 80.0


def test_mixed_entries():
    entries = [(ROLLOVER_IN, 40.0), (SPEND, 20.0), (ADJUST, 5.0), (SPEND, 49.99)]
    # 100 + 40 - 20 + 5 - 49.99
    assert compute_available(100.0, entries) == 75.01


def test_rollover_capped_at_1x_base():
    # unspent 140 but cap = 1x base(100) -> 100
    assert compute_rollover(140.0, 100.0, 1.0) == 100.0


def test_rollover_floored_at_zero():
    assert compute_rollover(-10.0, 100.0, 1.0) == 0.0


def test_rejects_negative_amounts():
    try:
        compute_available(100.0, [(SPEND, -5.0)])
    except ValueError:
        return
    raise AssertionError("expected ValueError on negative amount")


def test_rejects_unknown_type():
    try:
        compute_available(100.0, [("MYSTERY", 5.0)])
    except ValueError:
        return
    raise AssertionError("expected ValueError on unknown type")
