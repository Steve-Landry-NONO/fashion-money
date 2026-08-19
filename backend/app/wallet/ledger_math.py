"""Pure, dependency-free budget math (VS-05).

The wallet is an append-only ledger. The balance is *derived*, never stored.
Keeping this logic pure makes it trivially testable and swappable, and it is
the single source of truth reused by the SQLAlchemy service layer.
"""
from __future__ import annotations

# Ledger entry types
SPEND = "SPEND"
ADJUST = "ADJUST"
ROLLOVER_IN = "ROLLOVER_IN"

_VALID_TYPES = {SPEND, ADJUST, ROLLOVER_IN}


def compute_available(base_amount: float, entries: list[tuple[str, float]]) -> float:
    """Return the available balance for a period.

    available = base + Σ ROLLOVER_IN − Σ SPEND + Σ ADJUST

    `entries` is a list of (type, amount) for the *current* period only.
    Amounts are always stored positive; the sign is applied by type.
    """
    available = float(base_amount)
    for etype, amount in entries:
        if etype not in _VALID_TYPES:
            raise ValueError(f"unknown ledger type: {etype!r}")
        if amount < 0:
            raise ValueError("ledger amounts must be stored positive")
        if etype == SPEND:
            available -= amount
        else:  # ROLLOVER_IN or ADJUST both add to the envelope
            available += amount
    return round(available, 2)


def compute_rollover(available_end_of_month: float, base_amount: float,
                     cap_multiplier: float = 1.0) -> float:
    """Rollover credited into the next period (VS-06 readiness).

    Rolls over the unspent balance, floored at 0 and capped at
    cap_multiplier × base (default 1× → next-period available ≤ 2× base).
    """
    rollover = max(0.0, available_end_of_month)
    cap = cap_multiplier * float(base_amount)
    return round(min(rollover, cap), 2)
