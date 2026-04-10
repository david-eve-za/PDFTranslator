-- database/schemas/004_chapters.sql
CREATE TABLE IF NOT EXISTS chapters (
    id SERIAL PRIMARY KEY,
    volume_id INTEGER NOT NULL REFERENCES volumes(id) ON DELETE CASCADE,
    chapter_number INTEGER NOT NULL,
    title VARCHAR(500),
    start_position INTEGER,
    end_position INTEGER,
    original_text TEXT,
    translated_text TEXT,
    embedding vector(1536),
    created_at TIMESTAMP DEFAULT NOW(),
    CONSTRAINT unique_volume_chapter UNIQUE(volume_id, chapter_number)
);

CREATE INDEX idx_chapters_content_trgm ON chapters USING gin(original_text gin_trgm_ops);
CREATE INDEX idx_chapters_embedding ON chapters USING ivfflat (embedding vector_cosine_ops);
