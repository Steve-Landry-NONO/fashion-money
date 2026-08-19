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
