# Slice refinements applied (before first commit)

Four refinements from the backlog review are baked into this scaffold:

1. **Walking skeleton first (Jalon A).** Build order crosses all layers to reach:
   *100 € → mock capture → option → `fits` → decision → confirmed purchase →
   wallet debited → item added → activation recorded* — not horizontal layers.

2. **Purchase invariants (VS-14).** `budget_ledger` has
   `uq_ledger_idempotency (user_id, idempotency_key)` so `/purchases/confirm`
   is replay-safe (double POST, same key → one SPEND + one item). The confirm
   handler must run create-purchase + SPEND + wardrobe-item in ONE transaction;
   an integration test must assert full rollback if any step fails.

3. **Rollover idempotence (VS-06).** a **partial unique index** `uq_rollover_once_per_period` on
   `(user_id, period)` **where `type='ROLLOVER_IN'`** lets the monthly job be
   replayed after a crash without ever double-crediting — while still allowing
   many SPEND/ADJUST rows per period.

4. **Server-authoritative activation (VS-11/VS-15).** The `decision_actions`
   table + a future `POST /decisions/{id}/actions` persist the action
   server-side; the backend then emits `decision_action_taken`. The activation
   metric never depends on a client event that could be lost or duplicated.

## Matching calibration after real Vision

5. **`owned_pct` is now a normalized agreement rate over comparable attributes.**
   Before the collage-aware Vision work, `owned_pct` behaved like an absolute
   weighted score over the full 100-point attribute grid. With Qwen 3.8 deliberately
   leaving uncertain attributes such as `material` null, that would penalize good
   matches for missing evidence. The score is therefore normalized over attributes
   present on both the detected piece and wardrobe item.

   This changes the semantic meaning of the field and of analytics carrying it:
   values from before and after this change must not be compared as if they were on
   the same scale.

6. **Ownership requires enough comparable evidence.** A normalized 100% agreement
   based on too little information is not sufficient. At least 65 points of the
   original evidence weights must be comparable before a match can cross the
   `OWNED_THRESHOLD=75`. In practice, `category + color` is sufficient evidence;
   `category + cut` or `category + material` alone is not.

7. **Candidate ranking prefers richer evidence, not sparse certainty.** When multiple
   wardrobe items are plausible, ranking considers ownership eligibility first,
   then matched evidence weight, then total comparable evidence weight, then the
   normalized score. This prevents a vaguely described wardrobe item from beating a
   richer item only because missing attributes reduce its denominator.
