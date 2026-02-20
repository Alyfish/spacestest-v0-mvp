-- Add 'inspiration' to the improvement_mode check constraint
ALTER TABLE projects DROP CONSTRAINT IF EXISTS projects_improvement_mode_check;
ALTER TABLE projects ADD CONSTRAINT projects_improvement_mode_check
  CHECK (improvement_mode IS NULL OR improvement_mode IN ('iterative', 'complete_revamp', 'inspiration'));
