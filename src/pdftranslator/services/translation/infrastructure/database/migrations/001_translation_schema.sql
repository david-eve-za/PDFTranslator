"""
Translation Service Database Schema.
"""

-- Translation Jobs table
CREATE TABLE IF NOT EXISTS translation_jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    uuid TEXT NOT NULL UNIQUE,
    source_lang TEXT NOT NULL CHECK(length(source_lang) = 2),
    target_lang TEXT NOT NULL CHECK(length(target_lang) = 2),
    work_id INTEGER NOT NULL,
    volume_id INTEGER,
    status TEXT NOT NULL DEFAULT 'pending' CHECK(status IN ('pending', 'queued', 'in_progress', 'completed', 'failed', 'paused', 'cancelled')),
    priority INTEGER NOT NULL DEFAULT 50,
    source_text TEXT,
    target_text TEXT,
    llm_provider TEXT,
    model_name TEXT,
    error_message TEXT,
    started_at TEXT,
    completed_at TEXT,
    glossary_refs TEXT NOT NULL DEFAULT '[]',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    CHECK (source_lang != target_lang)
);

CREATE INDEX IF NOT EXISTS idx_translation_jobs_work_id ON translation_jobs(work_id);
CREATE INDEX IF NOT EXISTS idx_translation_jobs_status ON translation_jobs(status);
CREATE INDEX IF NOT EXISTS idx_translation_jobs_uuid ON translation_jobs(uuid);
CREATE INDEX IF NOT EXISTS idx_translation_jobs_created_at ON translation_jobs(created_at);


-- Translation Segments table
CREATE TABLE IF NOT EXISTS translation_segments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    uuid TEXT NOT NULL UNIQUE,
    job_id INTEGER NOT NULL REFERENCES translation_jobs(id) ON DELETE CASCADE,
    segment_number INTEGER CHECK(segment_number > 0),
    source_text TEXT,
    target_text TEXT,
    context_before TEXT,
    context_after TEXT,
    notes TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(job_id, segment_number)
);

CREATE INDEX IF NOT EXISTS idx_translation_segments_job_id ON translation_segments(job_id);
CREATE INDEX IF NOT EXISTS idx_translation_segments_uuid ON translation_segments(uuid);