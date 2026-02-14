-- Migration: Create jobs table for background task management
-- Run this in Supabase SQL Editor

-- Required for gen_random_uuid()
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- Jobs table
CREATE TABLE IF NOT EXISTS public.jobs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  project_id TEXT NOT NULL,

  job_type TEXT NOT NULL CHECK (job_type IN (
    'generate_image', 'inspiration_redesign', 'search_recommendations'
  )),

  status TEXT NOT NULL DEFAULT 'queued' CHECK (status IN (
    'queued', 'processing', 'done', 'error', 'cancelled'
  )),

  progress_pct INT NOT NULL DEFAULT 0 CHECK (progress_pct BETWEEN 0 AND 100),
  phase TEXT,

  -- MVP reliability: retries + restart safety
  attempts INT NOT NULL DEFAULT 0,
  locked_at TIMESTAMPTZ,
  locked_by TEXT,
  started_at TIMESTAMPTZ,
  finished_at TIMESTAMPTZ,

  -- Prevent duplicate jobs from retry/double tap
  idempotency_key TEXT,

  -- Debug + response payloads
  request JSONB,
  result JSONB,
  error TEXT,
  error_code TEXT,
  error_trace TEXT,

  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  expires_at TIMESTAMPTZ DEFAULT (NOW() + INTERVAL '1 hour')
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_jobs_user_project ON public.jobs(user_id, project_id);
CREATE INDEX IF NOT EXISTS idx_jobs_status_expires ON public.jobs(status, expires_at);
CREATE INDEX IF NOT EXISTS idx_jobs_locked_at ON public.jobs(locked_at);

-- Idempotency uniqueness (prevents duplicate jobs from retry/double-tap)
CREATE UNIQUE INDEX IF NOT EXISTS uq_jobs_idempotency
ON public.jobs(user_id, project_id, job_type, idempotency_key)
WHERE idempotency_key IS NOT NULL;

-- Auto-update timestamp trigger
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS jobs_updated_at ON public.jobs;
CREATE TRIGGER jobs_updated_at
BEFORE UPDATE ON public.jobs
FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- RLS: Users see only their jobs
ALTER TABLE public.jobs ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS jobs_select_own ON public.jobs;
CREATE POLICY jobs_select_own ON public.jobs
FOR SELECT USING (auth.uid() = user_id);

DROP POLICY IF EXISTS jobs_insert_own ON public.jobs;
CREATE POLICY jobs_insert_own ON public.jobs
FOR INSERT WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS jobs_update_own ON public.jobs;
CREATE POLICY jobs_update_own ON public.jobs
FOR UPDATE USING (auth.uid() = user_id);

DROP POLICY IF EXISTS jobs_delete_own ON public.jobs;
CREATE POLICY jobs_delete_own ON public.jobs
FOR DELETE USING (auth.uid() = user_id);

-- Requeue stale jobs function (call from app or pg_cron)
CREATE OR REPLACE FUNCTION requeue_stale_jobs(
  lease_seconds INT DEFAULT 300,
  max_attempts INT DEFAULT 3
)
RETURNS INT AS $$
DECLARE
  requeued INT;
BEGIN
  -- Requeue jobs that are stuck processing (stale lease)
  UPDATE public.jobs
  SET status = 'queued', locked_at = NULL, locked_by = NULL
  WHERE status = 'processing'
    AND locked_at < NOW() - (lease_seconds || ' seconds')::INTERVAL
    AND attempts < max_attempts;
  GET DIAGNOSTICS requeued = ROW_COUNT;

  -- Mark jobs that exceeded max attempts as error
  UPDATE public.jobs
  SET
    status = 'error',
    error = 'Max attempts exceeded',
    error_code = 'MAX_ATTEMPTS',
    finished_at = NOW()
  WHERE status = 'processing'
    AND locked_at < NOW() - (lease_seconds || ' seconds')::INTERVAL
    AND attempts >= max_attempts;

  RETURN requeued;
END;
$$ LANGUAGE plpgsql;

-- Cleanup expired jobs function
CREATE OR REPLACE FUNCTION cleanup_expired_jobs()
RETURNS INT AS $$
DECLARE
  deleted INT;
BEGIN
  DELETE FROM public.jobs
  WHERE expires_at < NOW()
    AND status IN ('done', 'error', 'cancelled');
  GET DIAGNOSTICS deleted = ROW_COUNT;
  RETURN deleted;
END;
$$ LANGUAGE plpgsql;

-- Grant execute permissions
GRANT EXECUTE ON FUNCTION requeue_stale_jobs TO service_role;
GRANT EXECUTE ON FUNCTION cleanup_expired_jobs TO service_role;
