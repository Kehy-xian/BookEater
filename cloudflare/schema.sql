-- Only explicit opt-in improvement examples live here. User libraries remain local SQLite.
-- contributor_hash is SHA-256 of a random local contributor secret; it is not an account, email, device id, or IP.
CREATE TABLE IF NOT EXISTS improvement_examples (
  example_id TEXT PRIMARY KEY,
  created_at TEXT NOT NULL,
  app_version TEXT NOT NULL,
  contributor_hash TEXT NOT NULL,
  text_hash TEXT NOT NULL,
  record_text TEXT NOT NULL,
  predicted_response TEXT NOT NULL DEFAULT '[]',
  predicted_world TEXT NOT NULL DEFAULT '[]',
  corrected_response TEXT NOT NULL DEFAULT '[]',
  corrected_world TEXT NOT NULL DEFAULT '[]',
  correction_provided INTEGER NOT NULL DEFAULT 0,
  feedback_signal TEXT NOT NULL DEFAULT '',
  auxiliary_tags TEXT NOT NULL DEFAULT '[]',
  model_backend TEXT NOT NULL,
  model_confidence REAL,
  consent_version TEXT NOT NULL,
  received_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_improvement_received_at ON improvement_examples(received_at);
CREATE INDEX IF NOT EXISTS idx_improvement_model_backend ON improvement_examples(model_backend);
CREATE INDEX IF NOT EXISTS idx_improvement_contributor ON improvement_examples(contributor_hash);
CREATE UNIQUE INDEX IF NOT EXISTS idx_improvement_dedupe
  ON improvement_examples(contributor_hash, text_hash, model_backend, correction_provided, corrected_response, corrected_world, feedback_signal);

-- Book-search caching intentionally does NOT use D1. The Worker Cache API holds short-lived provider responses,
-- which keeps D1 writes/reads reserved for the small opt-in improvement corpus.
