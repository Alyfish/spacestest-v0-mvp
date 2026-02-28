# Credit System: How It Works

## Overview

Credits are the currency for redesigns. Users start with 3 free credits and can purchase more via in-app credit packs (+2 each). Pro yearly subscribers get an annual grant.

## Idempotency

Every credit-mutating path uses an **idempotency key** to prevent double-grants or double-debits. The key is stored in `credit_transactions.idempotency_key` and protected by a unique partial index (`uq_credit_transactions_idempotency` from migration 006).

### How `add_credits()` works (migration 007)

The SQL function accepts 5 params: `p_user_id, p_amount, p_description, p_transaction_type, p_idempotency_key`.

- **Key is NULL**: skip idempotency check, behave like the original function (backward compat).
- **Key is provided**:
  1. `FOR UPDATE` lock on `user_credits` row (serialises concurrent calls for same user)
  2. Check if key exists in `credit_transactions` — if yes, return current balance (no-op)
  3. Otherwise, proceed with credit add + insert transaction row with the key
  4. The unique partial index is a safety net if two transactions somehow slip past the check

### How `check_and_debit_redesign()` works (migration 006)

Same pattern but for debits. Locks the row, checks idempotency, then validates balance / daily cap / cooldown before debiting.

## Idempotency Keys by Path

| Path | Key format | Notes |
|------|-----------|-------|
| RevenueCat webhook (credit pack) | `rc:{event_id}` | Passed directly to `add_credits` RPC. Dedupes webhook retries. |
| RevenueCat webhook (annual grant) | `rc:{event_id}` | Stamped on the `credit_transactions` row during insert. |
| `/dev/grant-credits` | `dev_credits:{user_id}:{timestamp_micros}` | Unique per call (microsecond precision). Passed to `add_credits` RPC. |
| `/inspiration-redesign` (client-provided) | Whatever the client sends in `X-Idempotency-Key` | Best option. Client controls retry semantics. |
| `/inspiration-redesign` (fallback) | `redesign:{user_id}:{project_id}:{minute_bucket}` | See tradeoffs below. |

## Inspiration-Redesign Fallback Key: Known Tradeoffs

When no `X-Idempotency-Key` header is provided, the fallback key uses a **60-second time bucket**:

```python
f"redesign:{user.id}:{project_id}:{int(time.time()) // 60}"
```

### Why 60 seconds

- The cooldown between redesigns is 30 seconds
- A 60-second bucket is 2x the cooldown, so retries of the same action (within the same minute window) dedup correctly
- The next legitimate redesign (30s+ later) will almost always land in a different minute bucket

### Known limitation

If a user starts two **legitimately different** redesigns for the **same project** within the same 60-second window, the second one will be treated as a duplicate of the first and silently deduped. This can happen if:

- The user cancels mid-generation and immediately retries (but with different input)
- The UI triggers two rapid calls with different parameters

In practice this is unlikely because:
1. The 30-second cooldown already prevents rapid-fire calls
2. Same project + same minute window + different intent is a narrow edge case

### Future improvements (if needed)

In order of preference:
1. **Client-provided `X-Idempotency-Key`** — best solution, client controls retry semantics. The Flutter app should generate a UUID per user action and send it in the header.
2. **`attempt_id` in request body** — if added to the API contract, would give a stable per-attempt identifier.
3. **Input fingerprint** — hash of (style, colors, markers, prompt) to distinguish different redesigns for the same project. More complex but fully deterministic.

## Deployment Order

Migration 007 **must** run before deploying updated `main.py`. The new function signature has `DEFAULT NULL` on `p_idempotency_key`, so old code calling with 4 params continues to work during the rollout window.

The old 4-param `add_credits` is DROPped in migration 007. This is intentional: Supabase/PostgREST resolves `.rpc("add_credits", {...})` by name, and two overloads with the same name cause ambiguous resolution. The new 5-param version with defaults handles all callers.

## RevenueCat / Mobile Runtime Notes

- `REVENUECAT_SECRET_KEY` stays backend-only (webhooks/server integrations). Do not ship it to the iOS app.
- The iOS app uses the RevenueCat **public** SDK key via Flutter `--dart-define` (`RC_API_KEY` or `REVENUECAT_PUBLIC_KEY`).
- Local helper scripts can source `backend/.env` and forward only `REVENUECAT_PUBLIC_KEY` to Flutter for device testing.
- Mock billing E2E (`/dev/grant-annual`, `/dev/grant-credits`) depends on `DEV_IAP_ENABLED=true` on the backend and `DEV_IAP_ENABLED=true` in Flutter dart-defines.
