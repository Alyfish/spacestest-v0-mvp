-- Migration 006: Credit System v2 — plan-tier, daily caps, cooldown, idempotency
-- Replaces the old "count rows to check limits" approach with an atomic
-- check_and_debit_redesign() stored procedure.
-- Run after 002_create_projects_tables.sql (which creates user_credits / credit_transactions).

-- ============================================================
-- 1. ADD NEW COLUMNS TO user_credits
-- ============================================================
ALTER TABLE public.user_credits
  ADD COLUMN IF NOT EXISTS plan_tier TEXT NOT NULL DEFAULT 'free'
    CHECK (plan_tier IN ('free', 'pro_yearly')),
  ADD COLUMN IF NOT EXISTS redesigns_used_today INT NOT NULL DEFAULT 0,
  ADD COLUMN IF NOT EXISTS daily_window_start DATE NOT NULL DEFAULT CURRENT_DATE,
  ADD COLUMN IF NOT EXISTS last_generation_started_at TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS credits_renew_at TIMESTAMPTZ;

-- ============================================================
-- 2. ADD IDEMPOTENCY TO credit_transactions
-- ============================================================
ALTER TABLE public.credit_transactions
  ADD COLUMN IF NOT EXISTS idempotency_key TEXT;

CREATE UNIQUE INDEX IF NOT EXISTS uq_credit_transactions_idempotency
  ON public.credit_transactions(idempotency_key)
  WHERE idempotency_key IS NOT NULL;

-- Expand the transaction_type CHECK constraint to include new types
-- (DROP + re-ADD because ALTER CONSTRAINT is not supported in PG < 12 simply)
ALTER TABLE public.credit_transactions
  DROP CONSTRAINT IF EXISTS credit_transactions_transaction_type_check;
ALTER TABLE public.credit_transactions
  ADD CONSTRAINT credit_transactions_transaction_type_check
  CHECK (transaction_type IN (
    'purchase',
    'generation_debit',
    'redesign_debit',
    'search_debit',
    'refund',
    'bonus',
    'signup_bonus',
    'annual_grant',
    'credit_purchase'
  ));

-- ============================================================
-- 3. ensure_user_credits() — init new users with 3 free credits
-- ============================================================
CREATE OR REPLACE FUNCTION ensure_user_credits(p_user_id UUID)
RETURNS VOID AS $$
BEGIN
  INSERT INTO public.user_credits (user_id, balance, total_purchased, plan_tier)
  VALUES (p_user_id, 3, 0, 'free')
  ON CONFLICT (user_id) DO NOTHING;
END;
$$ LANGUAGE plpgsql;

GRANT EXECUTE ON FUNCTION ensure_user_credits TO service_role;

-- ============================================================
-- 4. check_and_debit_redesign() — atomic debit with all guards
-- ============================================================
-- Returns a JSON object with either {ok: true, ...} or {ok: false, reason: ...}
CREATE OR REPLACE FUNCTION check_and_debit_redesign(
  p_user_id UUID,
  p_idempotency_key TEXT,
  p_project_id UUID DEFAULT NULL,
  p_description TEXT DEFAULT 'redesign'
)
RETURNS JSONB AS $$
DECLARE
  v_row public.user_credits%ROWTYPE;
  v_daily_cap INT;
  v_cooldown_seconds INT := 30;
  v_seconds_since_last NUMERIC;
  v_new_balance INT;
BEGIN
  -- 0. Ensure user row exists (first-time user)
  PERFORM ensure_user_credits(p_user_id);

  -- 1. Lock the row for update
  SELECT * INTO v_row
  FROM public.user_credits
  WHERE user_id = p_user_id
  FOR UPDATE;

  -- 2. Idempotency: if this key was already used, return success (no-op)
  IF p_idempotency_key IS NOT NULL THEN
    IF EXISTS (
      SELECT 1 FROM public.credit_transactions
      WHERE idempotency_key = p_idempotency_key
    ) THEN
      RETURN jsonb_build_object(
        'ok', true,
        'idempotent_hit', true,
        'balance', v_row.balance,
        'plan_tier', v_row.plan_tier
      );
    END IF;
  END IF;

  -- 3. Reset daily counter if window has rolled over
  IF v_row.daily_window_start < CURRENT_DATE THEN
    UPDATE public.user_credits
    SET redesigns_used_today = 0,
        daily_window_start = CURRENT_DATE
    WHERE user_id = p_user_id;
    v_row.redesigns_used_today := 0;
    v_row.daily_window_start := CURRENT_DATE;
  END IF;

  -- 4. Check balance
  IF v_row.balance < 1 THEN
    RETURN jsonb_build_object(
      'ok', false,
      'reason', 'insufficient_credits',
      'balance', v_row.balance,
      'plan_tier', v_row.plan_tier
    );
  END IF;

  -- 5. Daily cap check
  v_daily_cap := CASE v_row.plan_tier
    WHEN 'pro_yearly' THEN 5
    ELSE 3  -- free
  END;

  IF v_row.redesigns_used_today >= v_daily_cap THEN
    RETURN jsonb_build_object(
      'ok', false,
      'reason', 'daily_cap_reached',
      'daily_cap', v_daily_cap,
      'redesigns_used_today', v_row.redesigns_used_today,
      'plan_tier', v_row.plan_tier
    );
  END IF;

  -- 6. Cooldown check (30 seconds between generations)
  IF v_row.last_generation_started_at IS NOT NULL THEN
    v_seconds_since_last := EXTRACT(EPOCH FROM (NOW() - v_row.last_generation_started_at));
    IF v_seconds_since_last < v_cooldown_seconds THEN
      RETURN jsonb_build_object(
        'ok', false,
        'reason', 'cooldown',
        'cooldown_remaining', CEIL(v_cooldown_seconds - v_seconds_since_last),
        'plan_tier', v_row.plan_tier
      );
    END IF;
  END IF;

  -- 7. All checks passed — atomic debit
  UPDATE public.user_credits
  SET balance = balance - 1,
      total_used = total_used + 1,
      redesigns_used_today = redesigns_used_today + 1,
      last_generation_started_at = NOW()
  WHERE user_id = p_user_id AND balance >= 1
  RETURNING balance INTO v_new_balance;

  IF NOT FOUND THEN
    -- Race condition: someone else debited between our SELECT and UPDATE
    RETURN jsonb_build_object(
      'ok', false,
      'reason', 'insufficient_credits',
      'balance', 0,
      'plan_tier', v_row.plan_tier
    );
  END IF;

  -- 8. Record the transaction
  INSERT INTO public.credit_transactions
    (user_id, amount, balance_after, transaction_type, project_id, description, idempotency_key)
  VALUES
    (p_user_id, -1, v_new_balance, 'generation_debit', p_project_id, p_description, p_idempotency_key);

  RETURN jsonb_build_object(
    'ok', true,
    'balance', v_new_balance,
    'redesigns_used_today', v_row.redesigns_used_today + 1,
    'daily_cap', v_daily_cap,
    'plan_tier', v_row.plan_tier
  );
END;
$$ LANGUAGE plpgsql;

GRANT EXECUTE ON FUNCTION check_and_debit_redesign TO service_role;
