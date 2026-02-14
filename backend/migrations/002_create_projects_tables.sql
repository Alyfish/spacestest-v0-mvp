-- Migration 002: Create project tables for Supabase data storage
-- Run this in Supabase SQL Editor AFTER 001_create_jobs_table.sql
--
-- Tables created:
--   1. projects          — Main project data (replaces data/projects.json)
--   2. project_images    — Image references in Supabase Storage
--   3. improvement_markers — User-placed improvement markers
--   4. user_credits      — Credit balance per user
--   5. credit_transactions — Credit audit log
--
-- Also creates:
--   - deduct_credits() function for atomic credit deduction
--   - updated_at triggers on projects and user_credits

-- ============================================================
-- 1. PROJECTS TABLE
-- ============================================================
CREATE TABLE IF NOT EXISTS public.projects (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,

  -- Project status (matches STATUS_ORDER in data_manager.py)
  status TEXT NOT NULL DEFAULT 'NEW' CHECK (status IN (
    'NEW',
    'BASE_IMAGE_UPLOADED',
    'SPACE_TYPE_SELECTED',
    'IMPROVEMENT_MARKERS_SAVED',
    'MARKER_RECOMMENDATIONS_READY',
    'INSPIRATION_IMAGES_UPLOADED',
    'INSPIRATION_RECOMMENDATIONS_READY',
    'PRODUCT_RECOMMENDATIONS_READY',
    'PRODUCT_RECOMMENDATION_SELECTED',
    'PRODUCT_SEARCH_COMPLETE',
    'PRODUCT_SELECTED',
    'IMAGE_GENERATED',
    'INSPIRATION_REDESIGN_COMPLETE'
  )),

  -- Queryable scalar fields (from ProjectContext in models.py:502-613)
  space_type TEXT,
  improvement_mode TEXT CHECK (improvement_mode IS NULL OR improvement_mode IN ('iterative', 'complete_revamp')),
  is_base_image_empty_room BOOLEAN DEFAULT NULL,
  inspiration_images_skipped BOOLEAN DEFAULT FALSE,
  color_analysis_skipped BOOLEAN DEFAULT FALSE,
  style_analysis_skipped BOOLEAN DEFAULT FALSE,

  -- Lists of strings (small, potentially queryable via ANY())
  marker_recommendations TEXT[] DEFAULT '{}',
  inspiration_recommendations TEXT[] DEFAULT '{}',
  product_recommendations TEXT[] DEFAULT '{}',
  selected_product_recommendations TEXT[] DEFAULT '{}',
  preferred_stores TEXT[] DEFAULT '{}',

  -- Complex nested structures stored as JSONB
  -- These don't benefit from normalization — they're opaque blobs
  color_analysis JSONB,                         -- ColorAnalysis model output
  style_analysis JSONB,                         -- StyleAnalysis model output
  color_scheme JSONB,                           -- {palette_name, colors, let_ai_decide}
  design_style JSONB,                           -- {style_name, ...}
  pre_searched_categories JSONB DEFAULT '{}',   -- {recommendation: PreSearchedCategory}

  -- Lists of dicts (variable schema, stored as JSONB arrays)
  product_search_results JSONB DEFAULT '[]',    -- Exa/SERP search results
  selected_products JSONB DEFAULT '[]',         -- Products chosen for generation
  favorite_products JSONB DEFAULT '[]',         -- From "Like These?" screen
  selected_trending_products JSONB DEFAULT '[]', -- Trending products for generation

  -- Auto-selected product from scoring algorithm
  auto_selected_product JSONB,

  -- Generation metadata (text only — images go to Storage)
  generation_prompt TEXT,
  generation_model_used TEXT,
  inspiration_generation_prompt TEXT,
  inspiration_model_used TEXT,

  -- Timestamps
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for common query patterns
CREATE INDEX IF NOT EXISTS idx_projects_user_id ON public.projects(user_id);
CREATE INDEX IF NOT EXISTS idx_projects_user_status ON public.projects(user_id, status);
CREATE INDEX IF NOT EXISTS idx_projects_created_at ON public.projects(created_at DESC);

-- Auto-update updated_at (reuses function from 001_create_jobs_table.sql)
DROP TRIGGER IF EXISTS projects_updated_at ON public.projects;
CREATE TRIGGER projects_updated_at
BEFORE UPDATE ON public.projects
FOR EACH ROW EXECUTE FUNCTION update_updated_at();


-- ============================================================
-- 2. PROJECT IMAGES TABLE
-- ============================================================
-- Tracks all images for a project stored in Supabase Storage.
-- One row per image file. Generated images go here too (not as base64 in projects).
CREATE TABLE IF NOT EXISTS public.project_images (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id UUID NOT NULL REFERENCES public.projects(id) ON DELETE CASCADE,
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,

  -- Image type discriminator
  image_type TEXT NOT NULL CHECK (image_type IN (
    'base',                    -- Original room photo
    'labelled',                -- Room photo with markers drawn on it
    'inspiration',             -- User-uploaded inspiration image
    'generated',               -- AI-generated product visualization
    'inspiration_generated'    -- AI-generated inspiration redesign
  )),

  -- Supabase Storage references
  storage_path TEXT NOT NULL,  -- Path within bucket, e.g. "{project_id}/base/room.jpg"
  public_url TEXT,             -- Pre-computed public URL for frontend use

  -- Ordering (for inspiration images: 0, 1, 2, ...)
  sort_order INT DEFAULT 0,

  -- File metadata
  original_filename TEXT,
  mime_type TEXT DEFAULT 'image/png',
  file_size_bytes BIGINT,

  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_project_images_project_type ON public.project_images(project_id, image_type);
CREATE INDEX IF NOT EXISTS idx_project_images_user ON public.project_images(user_id);


-- ============================================================
-- 3. IMPROVEMENT MARKERS TABLE
-- ============================================================
-- Separate from projects table for structured queries and clean upsert.
-- Maps to ImprovementMarker model in models.py:439-458.
CREATE TABLE IF NOT EXISTS public.improvement_markers (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id UUID NOT NULL REFERENCES public.projects(id) ON DELETE CASCADE,
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,

  -- Marker data
  marker_id TEXT NOT NULL,          -- Client-provided marker ID
  position_x FLOAT NOT NULL CHECK (position_x >= 0.0 AND position_x <= 1.0),
  position_y FLOAT NOT NULL CHECK (position_y >= 0.0 AND position_y <= 1.0),
  description TEXT NOT NULL,
  color TEXT NOT NULL,              -- "red", "green", "blue", "purple", "orange"

  sort_order INT DEFAULT 0,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_markers_project ON public.improvement_markers(project_id);
CREATE UNIQUE INDEX IF NOT EXISTS uq_markers_project_marker ON public.improvement_markers(project_id, marker_id);


-- ============================================================
-- 4. USER CREDITS TABLE
-- ============================================================
CREATE TABLE IF NOT EXISTS public.user_credits (
  user_id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  balance INT NOT NULL DEFAULT 0 CHECK (balance >= 0),
  total_purchased INT NOT NULL DEFAULT 0,
  total_used INT NOT NULL DEFAULT 0,
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

DROP TRIGGER IF EXISTS user_credits_updated_at ON public.user_credits;
CREATE TRIGGER user_credits_updated_at
BEFORE UPDATE ON public.user_credits
FOR EACH ROW EXECUTE FUNCTION update_updated_at();


-- ============================================================
-- 5. CREDIT TRANSACTIONS TABLE
-- ============================================================
CREATE TABLE IF NOT EXISTS public.credit_transactions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,

  amount INT NOT NULL,             -- Positive = credit, negative = debit
  balance_after INT NOT NULL,

  transaction_type TEXT NOT NULL CHECK (transaction_type IN (
    'purchase',
    'generation_debit',
    'redesign_debit',
    'search_debit',
    'refund',
    'bonus',
    'signup_bonus'
  )),

  -- Optional references to what consumed the credit
  project_id UUID REFERENCES public.projects(id) ON DELETE SET NULL,
  job_id UUID REFERENCES public.jobs(id) ON DELETE SET NULL,

  description TEXT,

  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_credits_user_created ON public.credit_transactions(user_id, created_at DESC);


-- ============================================================
-- 6. ATOMIC CREDIT DEDUCTION FUNCTION
-- ============================================================
-- Prevents race conditions on concurrent generation requests.
-- Uses UPDATE ... WHERE balance >= amount (atomic check-and-decrement).
CREATE OR REPLACE FUNCTION deduct_credits(
  p_user_id UUID,
  p_amount INT,
  p_description TEXT,
  p_transaction_type TEXT DEFAULT 'generation_debit',
  p_project_id UUID DEFAULT NULL,
  p_job_id UUID DEFAULT NULL
)
RETURNS INT AS $$
DECLARE
  new_balance INT;
BEGIN
  -- Atomic decrement: only succeeds if balance >= amount
  UPDATE public.user_credits
  SET balance = balance - p_amount,
      total_used = total_used + p_amount
  WHERE user_id = p_user_id AND balance >= p_amount
  RETURNING balance INTO new_balance;

  IF NOT FOUND THEN
    RAISE EXCEPTION 'Insufficient credits: user=%, requested=%', p_user_id, p_amount;
  END IF;

  -- Record the transaction
  INSERT INTO public.credit_transactions
    (user_id, amount, balance_after, transaction_type, project_id, job_id, description)
  VALUES
    (p_user_id, -p_amount, new_balance, p_transaction_type, p_project_id, p_job_id, p_description);

  RETURN new_balance;
END;
$$ LANGUAGE plpgsql;

-- Add credits (for purchases, bonuses, refunds)
CREATE OR REPLACE FUNCTION add_credits(
  p_user_id UUID,
  p_amount INT,
  p_description TEXT,
  p_transaction_type TEXT DEFAULT 'purchase'
)
RETURNS INT AS $$
DECLARE
  new_balance INT;
BEGIN
  -- Upsert user_credits row (first purchase creates the row)
  INSERT INTO public.user_credits (user_id, balance, total_purchased)
  VALUES (p_user_id, p_amount, p_amount)
  ON CONFLICT (user_id)
  DO UPDATE SET
    balance = public.user_credits.balance + p_amount,
    total_purchased = public.user_credits.total_purchased + p_amount
  RETURNING balance INTO new_balance;

  -- Record the transaction
  INSERT INTO public.credit_transactions
    (user_id, amount, balance_after, transaction_type, description)
  VALUES
    (p_user_id, p_amount, new_balance, p_transaction_type, p_description);

  RETURN new_balance;
END;
$$ LANGUAGE plpgsql;

-- Grant execute to service role (backend uses service key)
GRANT EXECUTE ON FUNCTION deduct_credits TO service_role;
GRANT EXECUTE ON FUNCTION add_credits TO service_role;
