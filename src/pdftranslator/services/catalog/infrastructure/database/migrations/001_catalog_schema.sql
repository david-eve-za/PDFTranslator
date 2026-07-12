"""
Catalog Service Database Schema.

CUPID Principle: Predictable
- Explicit schema with constraints
- Foreign keys with cascade rules
- Indexes for common queries
"""

-- Works table (Aggregate Root)
CREATE TABLE IF NOT EXISTS works (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    uuid TEXT NOT NULL UNIQUE,
    title TEXT NOT NULL,
    title_translated TEXT,
    author TEXT,
    source_lang TEXT NOT NULL CHECK(length(source_lang) = 2),
    target_lang TEXT NOT NULL CHECK(length(target_lang) = 2),
    created_at TEXT NOT NULL,  -- ISO 8601
    updated_at TEXT NOT NULL,  -- ISO 8601
    CHECK (source_lang != target_lang)
);

CREATE INDEX IF NOT EXISTS idx_works_title ON works(title);
CREATE INDEX IF NOT EXISTS idx_works_uuid ON works(uuid);
CREATE INDEX IF NOT EXISTS idx_works_created_at ON works(created_at);


-- Volumes table (Entity within Work aggregate)
CREATE TABLE IF NOT EXISTS volumes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    uuid TEXT NOT NULL UNIQUE,
    work_id INTEGER NOT NULL REFERENCES works(id) ON DELETE CASCADE,
    volume_number INTEGER NOT NULL CHECK(volume_number > 0),
    title TEXT,
    full_text TEXT,
    translated_text TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    glossary_built_at TEXT,
    glossary_build_status TEXT NOT NULL DEFAULT 'pending' CHECK(glossary_build_status IN ('pending', 'in_progress', 'completed', 'failed')),
    glossary_error_message TEXT,
    glossary_resume_phase TEXT,
    UNIQUE(work_id, volume_number)
);

CREATE INDEX IF NOT EXISTS idx_volumes_work_id ON volumes(work_id);
CREATE INDEX IF NOT EXISTS idx_volumes_uuid ON volumes(uuid);


-- Chapters table (Entity within Volume aggregate)
CREATE TABLE IF NOT EXISTS chapters (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    uuid TEXT NOT NULL UNIQUE,
    volume_id INTEGER NOT NULL REFERENCES volumes(id) ON DELETE CASCADE,
    chapter_number INTEGER CHECK(chapter_number > 0),
    title TEXT,
    start_position INTEGER CHECK(start_position >= 0),
    end_position INTEGER CHECK(end_position >= 0),
    original_text TEXT,
    translated_text TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(volume_id, chapter_number)
);

CREATE INDEX IF NOT EXISTS idx_chapters_volume_id ON chapters(volume_id);
CREATE INDEX IF NOT EXISTS idx_chapters_uuid ON chapters(uuid);


-- View for work summary (convenience for listing)
CREATE VIEW IF NOT EXISTS work_summary AS
SELECT
    w.id,
    w.uuid,
    w.title,
    w.title_translated,
    w.author,
    w.source_lang,
    w.target_lang,
    w.created_at,
    w.updated_at,
    COUNT(DISTINCT v.id) as volume_count,
    COUNT(DISTINCT c.id) as total_chapters,
    COUNT(CASE WHEN c.translated_text IS NOT NULL AND c.translated_text != '' THEN 1 END) as translated_chapters
FROM works w
LEFT JOIN volumes v ON v.work_id = w.id
LEFT JOIN chapters c ON c.volume_id = v.id
GROUP BY w.id;