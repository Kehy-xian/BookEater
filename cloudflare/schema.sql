-- Only opt-in improvement examples live here. User libraries remain local SQLite.
CREATE TABLE IF NOT EXISTS improvement_examples (
  example_id TEXT PRIMARY KEY,
  created_at TEXT NOT NULL,
  app_version TEXT NOT NULL,
  install_pseudonym TEXT NOT NULL,
  record_text TEXT NOT NULL,
  predicted_response TEXT NOT NULL DEFAULT '[]',
  predicted_world TEXT NOT NULL DEFAULT '[]',
  corrected_response TEXT NOT NULL DEFAULT '[]',
  corrected_world TEXT NOT NULL DEFAULT '[]',
  auxiliary_tags TEXT NOT NULL DEFAULT '[]',
  model_backend TEXT NOT NULL,
  consent_version TEXT NOT NULL,
  received_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_improvement_received_at ON improvement_examples(received_at);
CREATE INDEX IF NOT EXISTS idx_improvement_model_backend ON improvement_examples(model_backend);

-- Small API cache to reduce Aladin calls. It never contains a user's reading archive.
CREATE TABLE IF NOT EXISTS book_search_cache (
  cache_key TEXT PRIMARY KEY,
  payload_json TEXT NOT NULL,
  expires_at INTEGER NOT NULL,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_book_cache_expires ON book_search_cache(expires_at);
