-- Existing D1 databases need these columns because CREATE TABLE IF NOT EXISTS will not alter them.
ALTER TABLE improvement_examples ADD COLUMN correction_provided INTEGER NOT NULL DEFAULT 0;
ALTER TABLE improvement_examples ADD COLUMN feedback_signal TEXT NOT NULL DEFAULT '';

DROP INDEX IF EXISTS idx_improvement_dedupe;
CREATE UNIQUE INDEX IF NOT EXISTS idx_improvement_dedupe
  ON improvement_examples(contributor_hash, text_hash, model_backend, correction_provided, corrected_response, corrected_world, feedback_signal);
