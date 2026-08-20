# Wave B analytics contract

This slice instruments the product states needed to evaluate H3 without changing product behavior.

## Core context

Every capture-related decision surface carries:

- `capture_index`: 1-based capture number for the user
- `wardrobe_count`: number of known wardrobe items at that moment
- `regime`: `j0` when the wardrobe is empty, otherwise `mature`

`match_computed` additionally carries `owned_pct`, which lets analysis compare wardrobe growth and match coverage over successive captures.

## H3 evidence path

A minimal compounding sequence is:

1. first capture: `capture_index=1`, `regime=j0`, `owned_pct=0`
2. confirmed purchase: wardrobe count increases
3. second capture: `capture_index=2`, `regime=mature`, `owned_pct>0`
4. `return_session` is emitted on capture 2+

This does not prove H3 by itself; it makes the hypothesis measurable in beta. H3 is supported only if higher capture indices / wardrobe coverage correlate with return behavior and continued decision actions.

## Activation invariant

`decision_viewed` remains non-activating. Activation is recorded only by server-side `decision_action_taken`.
