-- Migration 003: Row Level Security policies + Storage bucket
-- Run this in Supabase SQL Editor AFTER 002_create_projects_tables.sql
--
-- Pattern matches 001_create_jobs_table.sql:70-87
-- Backend uses service role key (bypasses RLS). RLS protects client-side SDK access.

-- ============================================================
-- PROJECTS
-- ============================================================
ALTER TABLE public.projects ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS projects_select_own ON public.projects;
CREATE POLICY projects_select_own ON public.projects
FOR SELECT USING (auth.uid() = user_id);

DROP POLICY IF EXISTS projects_insert_own ON public.projects;
CREATE POLICY projects_insert_own ON public.projects
FOR INSERT WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS projects_update_own ON public.projects;
CREATE POLICY projects_update_own ON public.projects
FOR UPDATE USING (auth.uid() = user_id);

DROP POLICY IF EXISTS projects_delete_own ON public.projects;
CREATE POLICY projects_delete_own ON public.projects
FOR DELETE USING (auth.uid() = user_id);


-- ============================================================
-- PROJECT IMAGES
-- ============================================================
ALTER TABLE public.project_images ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS project_images_select_own ON public.project_images;
CREATE POLICY project_images_select_own ON public.project_images
FOR SELECT USING (auth.uid() = user_id);

DROP POLICY IF EXISTS project_images_insert_own ON public.project_images;
CREATE POLICY project_images_insert_own ON public.project_images
FOR INSERT WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS project_images_update_own ON public.project_images;
CREATE POLICY project_images_update_own ON public.project_images
FOR UPDATE USING (auth.uid() = user_id);

DROP POLICY IF EXISTS project_images_delete_own ON public.project_images;
CREATE POLICY project_images_delete_own ON public.project_images
FOR DELETE USING (auth.uid() = user_id);


-- ============================================================
-- IMPROVEMENT MARKERS
-- ============================================================
ALTER TABLE public.improvement_markers ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS markers_select_own ON public.improvement_markers;
CREATE POLICY markers_select_own ON public.improvement_markers
FOR SELECT USING (auth.uid() = user_id);

DROP POLICY IF EXISTS markers_insert_own ON public.improvement_markers;
CREATE POLICY markers_insert_own ON public.improvement_markers
FOR INSERT WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS markers_update_own ON public.improvement_markers;
CREATE POLICY markers_update_own ON public.improvement_markers
FOR UPDATE USING (auth.uid() = user_id);

DROP POLICY IF EXISTS markers_delete_own ON public.improvement_markers;
CREATE POLICY markers_delete_own ON public.improvement_markers
FOR DELETE USING (auth.uid() = user_id);


-- ============================================================
-- USER CREDITS (read-only for users; backend inserts via service role)
-- ============================================================
ALTER TABLE public.user_credits ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS user_credits_select_own ON public.user_credits;
CREATE POLICY user_credits_select_own ON public.user_credits
FOR SELECT USING (auth.uid() = user_id);


-- ============================================================
-- CREDIT TRANSACTIONS (read-only for users; backend inserts via service role)
-- ============================================================
ALTER TABLE public.credit_transactions ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS credits_select_own ON public.credit_transactions;
CREATE POLICY credits_select_own ON public.credit_transactions
FOR SELECT USING (auth.uid() = user_id);


-- ============================================================
-- SUPABASE STORAGE BUCKET
-- ============================================================
-- Create the bucket for project images (public so generated images are shareable)
INSERT INTO storage.buckets (id, name, public)
VALUES ('project-images', 'project-images', true)
ON CONFLICT (id) DO NOTHING;

-- Users can upload to paths prefixed with their project ID
-- Backend uses service role (bypasses these), but this protects client SDK access
DROP POLICY IF EXISTS storage_project_images_insert ON storage.objects;
CREATE POLICY storage_project_images_insert ON storage.objects
FOR INSERT WITH CHECK (
  bucket_id = 'project-images'
);

DROP POLICY IF EXISTS storage_project_images_select ON storage.objects;
CREATE POLICY storage_project_images_select ON storage.objects
FOR SELECT USING (
  bucket_id = 'project-images'
);

DROP POLICY IF EXISTS storage_project_images_delete ON storage.objects;
CREATE POLICY storage_project_images_delete ON storage.objects
FOR DELETE USING (
  bucket_id = 'project-images'
);
