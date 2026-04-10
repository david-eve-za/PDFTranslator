-- database/schemas/003_volumes.sql
CREATE TABLE IF NOT EXISTS volumes (
    id SERIAL PRIMARY KEY,
    work_id INTEGER NOT NULL REFERENCES works(id) ON DELETE CASCADE,
    volume_number INTEGER NOT NULL,
    title VARCHAR(500),
    full_text TEXT,
    translated_text TEXT,
    embedding vector(1536),
    created_at TIMESTAMP DEFAULT NOW(),
    CONSTRAINT unique_work_volume UNIQUE(work_id, volume_number)
);

CREATE INDEX idx_volumes_embedding ON volumes USING ivfflat (embedding vector_cosine_ops);
