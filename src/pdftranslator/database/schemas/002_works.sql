-- database/schemas/002_works.sql
CREATE TABLE IF NOT EXISTS works (
    id SERIAL PRIMARY KEY,
    title VARCHAR(500) NOT NULL,
    title_translated VARCHAR(500),
    source_lang VARCHAR(10) DEFAULT 'en',
    target_lang VARCHAR(10) DEFAULT 'es',
    author VARCHAR(300),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_works_title_trgm ON works USING gin(title gin_trgm_ops);
