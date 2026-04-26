-- ============================================================================
-- Translation Jobs Table
-- ============================================================================
-- Tracks background translation jobs started from the API.
-- ============================================================================

CREATE TABLE IF NOT EXISTS translation_jobs (
    id SERIAL PRIMARY KEY,
    work_id INTEGER NOT NULL REFERENCES works(id) ON DELETE CASCADE,
    scope VARCHAR(20) NOT NULL,
    volume_id INTEGER REFERENCES volumes(id) ON DELETE SET NULL,
    chapter_id INTEGER REFERENCES chapters(id) ON DELETE SET NULL,
    source_lang VARCHAR(5) NOT NULL DEFAULT 'en',
    target_lang VARCHAR(5) NOT NULL DEFAULT 'es',
    skip_translated BOOLEAN NOT NULL DEFAULT TRUE,
    dry_run BOOLEAN NOT NULL DEFAULT FALSE,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    total_chapters INTEGER DEFAULT 0,
    completed_chapters INTEGER DEFAULT 0,
    success_count INTEGER DEFAULT 0,
    failure_count INTEGER DEFAULT 0,
    current_chapter_info TEXT,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_translation_jobs_work_id ON translation_jobs(work_id);
CREATE INDEX IF NOT EXISTS idx_translation_jobs_status ON translation_jobs(status);

CREATE OR REPLACE FUNCTION update_translation_job_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS update_translation_job_timestamp ON translation_jobs;
CREATE TRIGGER update_translation_job_timestamp
BEFORE UPDATE ON translation_jobs
FOR EACH ROW
EXECUTE FUNCTION update_translation_job_timestamp();
