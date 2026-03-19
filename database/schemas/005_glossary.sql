-- database/schemas/005_glossary.sql
CREATE TABLE IF NOT EXISTS glossary_terms (
    id SERIAL PRIMARY KEY,
    work_id INTEGER NOT NULL REFERENCES works(id) ON DELETE CASCADE,
    term VARCHAR(200) NOT NULL,
    translation VARCHAR(500),
    notes TEXT,
    is_proper_noun BOOLEAN DEFAULT FALSE,
    embedding vector(1536),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_glossary_term_trgm ON glossary_terms USING gin(term gin_trgm_ops);
CREATE INDEX idx_glossary_embedding ON glossary_terms USING ivfflat (embedding vector_cosine_ops);

CREATE TABLE IF NOT EXISTS term_contexts (
    id SERIAL PRIMARY KEY,
    term_id INTEGER NOT NULL REFERENCES glossary_terms(id) ON DELETE CASCADE,
    context_hint VARCHAR(200) NOT NULL,
    translation VARCHAR(500) NOT NULL,
    example_usage TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS context_examples (
    id SERIAL PRIMARY KEY,
    context_id INTEGER NOT NULL REFERENCES term_contexts(id) ON DELETE CASCADE,
    original_sentence TEXT NOT NULL,
    translated_sentence TEXT NOT NULL,
    chapter_id INTEGER REFERENCES chapters(id) ON DELETE SET NULL,
    created_at TIMESTAMP DEFAULT NOW()
);
