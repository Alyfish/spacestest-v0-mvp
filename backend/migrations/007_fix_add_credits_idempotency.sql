-- Migration 007: Fix add_credits idempotency race
-- Replaces the old 4-param add_credits() with a 5-param version that
-- accepts an optional p_idempotency_key. When provided, it locks the
-- user_credits row and checks credit_transactions before inserting,
-- preventing double-grants from webhook retries or client retries.
-- The existing unique partial index uq_credit_transactions_idempotency
-- (from migration 006) acts as a safety net on the INSERT.

-- Drop the old 4-param overload so there is exactly one version.
-- Why DROP instead of keeping both overloads: Supabase/PostgREST resolves
-- .rpc("add_credits", {...}) by function name. Two overloads with the same
-- name cause ambiguous resolution. The new 5-param version has DEFAULT NULL
-- on p_idempotency_key, so old callers passing 4 named params still work.
-- DEPLOYMENT: run this migration BEFORE deploying updated main.py.
DROP FUNCTION IF EXISTS add_credits(UUID, INT, TEXT, TEXT);

CREATE OR REPLACE FUNCTION add_credits(
  p_user_id UUID,
  p_amount INT,
  p_description TEXT,
  p_transaction_type TEXT DEFAULT 'purchase',
  p_idempotency_key TEXT DEFAULT NULL
)
RETURNS INT AS $$
DECLARE
  v_balance INT;
BEGIN
  -- 0. Ensure user row exists
  PERFORM ensure_user_credits(p_user_id);

  -- 1. If an idempotency key is provided, lock the row and check for dups
  IF p_idempotency_key IS NOT NULL THEN
    -- Lock user_credits row to serialise concurrent calls with the same key
    PERFORM 1 FROM public.user_credits
      WHERE user_id = p_user_id
      FOR UPDATE;

    -- If this key was already used, return current balance (no-op)
    IF EXISTS (
      SELECT 1 FROM public.credit_transactions
      WHERE idempotency_key = p_idempotency_key
    ) THEN
      SELECT balance INTO v_balance
        FROM public.user_credits
        WHERE user_id = p_user_id;
      RETURN v_balance;
    END IF;
  END IF;

  -- 2. Atomic credit add (upsert)
  INSERT INTO public.user_credits (user_id, balance, total_purchased)
  VALUES (p_user_id, p_amount, p_amount)
  ON CONFLICT (user_id)
  DO UPDATE SET
    balance = public.user_credits.balance + p_amount,
    total_purchased = public.user_credits.total_purchased + p_amount
  RETURNING balance INTO v_balance;

  -- 3. Record the transaction (unique index catches any remaining races)
  INSERT INTO public.credit_transactions
    (user_id, amount, balance_after, transaction_type, description, idempotency_key)
  VALUES
    (p_user_id, p_amount, v_balance, p_transaction_type, p_description, p_idempotency_key);

  RETURN v_balance;
END;
$$ LANGUAGE plpgsql;

GRANT EXECUTE ON FUNCTION add_credits TO service_role;
