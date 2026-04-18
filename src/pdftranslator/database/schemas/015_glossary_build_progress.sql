-- Progress tracking table for glossary build resume system
CREATE TABLE IF NOT EXISTS glossary_build_progress (
    id SERIAL PRIMARY KEY,
    work_id INTEGER NOT NULL REFERENCES works(id) ON DELETE CASCADE,
    volume_id INTEGER NOT NULL REFERENCES volumes(id) ON DELETE CASCADE,
    entity_text VARCHAR(200) NOT NULL,

    -- Phase tracking: extracted -> validated -> translated -> saved
    phase VARCHAR(20) NOT NULL DEFAULT 'extracted',

    -- Entity data
    entity_type VARCHAR(50),
    frequency INTEGER DEFAULT 1,
    contexts TEXT[],
    translation VARCHAR(500),
    embedding vector(1536),

    -- Batch tracking for resume
    validation_batch INTEGER,
    translation_batch INTEGER,

    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Unique constraint for case-insensitive entity_text (using unique index)
CREATE UNIQUE INDEX IF NOT EXISTS idx_progress_unique_entity ON glossary_build_progress(work_id, volume_id, LOWER(entity_text));

-- Indexes for efficient queries
CREATE INDEX IF NOT EXISTS idx_progress_work_volume ON glossary_build_progress(work_id, volume_id);
CREATE INDEX IF NOT EXISTS idx_progress_phase ON glossary_build_progress(phase);
CREATE INDEX IF NOT EXISTS idx_progress_resume ON glossary_build_progress(work_id, volume_id, phase) WHERE phase != 'saved';
CREATE INDEX IF NOT EXISTS idx_progress_pending ON glossary_build_progress(work_id, volume_id) WHERE phase IN ('extracted', 'validated', 'translated');

-- Extend volumes table with build status
ALTER TABLE volumes ADD COLUMN IF NOT EXISTS glossary_build_status VARCHAR(20) DEFAULT 'pending';
ALTER TABLE volumes ADD COLUMN IF NOT EXISTS glossary_error_message TEXT;
ALTER TABLE volumes ADD COLUMN IF NOT EXISTS glossary_resume_phase VARCHAR(20);
CREATE INDEX IF NOT EXISTS idx_volumes_build_status ON volumes(glossary_build_status);

-- Trigger to auto-update updated_at
CREATE OR REPLACE FUNCTION update_glossary_progress_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

DROP TRIGGER IF EXISTS update_glossary_progress_updated_at ON glossary_build_progress;
CREATE TRIGGER update_glossary_progress_updated_at
    BEFORE UPDATE ON glossary_build_progress
    FOR EACH ROW
    EXECUTE FUNCTION update_glossary_progress_updated_at();
