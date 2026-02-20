-- Migration 005: Per-job push notification subscriptions for "notify when ready"
-- Run after 001_create_jobs_table.sql, 002_create_projects_tables.sql, and 003_rls_policies.sql

CREATE TABLE IF NOT EXISTS public.job_ready_notifications (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  job_id UUID NOT NULL REFERENCES public.jobs(id) ON DELETE CASCADE,
  project_id TEXT NOT NULL,
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,

  device_token TEXT NOT NULL,
  platform TEXT NOT NULL CHECK (platform IN ('ios', 'android')),

  status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'sent', 'failed')),
  requested_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  sent_at TIMESTAMPTZ,
  last_error TEXT
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_job_ready_notifications_job_user_token
ON public.job_ready_notifications(job_id, user_id, device_token);

CREATE INDEX IF NOT EXISTS idx_job_ready_notifications_job
ON public.job_ready_notifications(job_id);

CREATE INDEX IF NOT EXISTS idx_job_ready_notifications_status
ON public.job_ready_notifications(status);

CREATE INDEX IF NOT EXISTS idx_job_ready_notifications_job_status
ON public.job_ready_notifications(job_id, status);

ALTER TABLE public.job_ready_notifications ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS job_ready_notifications_select_own ON public.job_ready_notifications;
CREATE POLICY job_ready_notifications_select_own ON public.job_ready_notifications
FOR SELECT USING (auth.uid() = user_id);

DROP POLICY IF EXISTS job_ready_notifications_insert_own ON public.job_ready_notifications;
CREATE POLICY job_ready_notifications_insert_own ON public.job_ready_notifications
FOR INSERT WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS job_ready_notifications_update_own ON public.job_ready_notifications;
CREATE POLICY job_ready_notifications_update_own ON public.job_ready_notifications
FOR UPDATE USING (auth.uid() = user_id);

DROP POLICY IF EXISTS job_ready_notifications_delete_own ON public.job_ready_notifications;
CREATE POLICY job_ready_notifications_delete_own ON public.job_ready_notifications
FOR DELETE USING (auth.uid() = user_id);
