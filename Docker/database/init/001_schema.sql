-- ============================================================================
-- PDFTranslator - Consolidated Database Schema
-- ============================================================================
-- This script creates the complete database schema from scratch.
-- All migration steps have been consolidated into their target tables.
-- ============================================================================

-- Extensions
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================================
-- TABLES
-- ============================================================================

-- Works
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

CREATE INDEX IF NOT EXISTS idx_works_title_trgm ON works USING gin(title gin_trgm_ops);

-- Volumes (includes glossary tracking from migrations 014/015)
CREATE TABLE IF NOT EXISTS volumes (
    id SERIAL PRIMARY KEY,
    work_id INTEGER NOT NULL REFERENCES works(id) ON DELETE CASCADE,
    volume_number INTEGER NOT NULL,
    title VARCHAR(500),
    full_text TEXT,
    translated_text TEXT,
    embedding vector(1024),
    glossary_built_at TIMESTAMP,
    glossary_build_status VARCHAR(20) DEFAULT 'pending',
    glossary_error_message TEXT,
    glossary_resume_phase VARCHAR(20),
    created_at TIMESTAMP DEFAULT NOW(),
    CONSTRAINT unique_work_volume UNIQUE(work_id, volume_number)
);

CREATE INDEX IF NOT EXISTS idx_volumes_embedding ON volumes USING ivfflat (embedding vector_cosine_ops);
CREATE INDEX IF NOT EXISTS idx_volumes_glossary_built ON volumes(glossary_built_at) WHERE glossary_built_at IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_volumes_build_status ON volumes(glossary_build_status);

-- Chapters (chapter_number nullable for Prologue/Epilogue, from migration 006)
CREATE TABLE IF NOT EXISTS chapters (
    id SERIAL PRIMARY KEY,
    volume_id INTEGER NOT NULL REFERENCES volumes(id) ON DELETE CASCADE,
    chapter_number INTEGER,
    title VARCHAR(500),
    start_position INTEGER,
    end_position INTEGER,
    original_text TEXT,
    translated_text TEXT,
    embedding vector(1024),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_unique_volume_chapter ON chapters(volume_id, chapter_number) WHERE chapter_number IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_chapters_content_trgm ON chapters USING gin(original_text gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_chapters_embedding ON chapters USING ivfflat (embedding vector_cosine_ops);

-- Glossary terms (includes NER fields from migration 007, frontend compat from 011)
CREATE TABLE IF NOT EXISTS glossary_terms (
    id SERIAL PRIMARY KEY,
    work_id INTEGER NOT NULL REFERENCES works(id) ON DELETE CASCADE,
    term VARCHAR(200) NOT NULL,
    translation VARCHAR(500),
    notes TEXT,
    is_proper_noun BOOLEAN DEFAULT FALSE,
    entity_type VARCHAR(50) DEFAULT 'other',
    do_not_translate BOOLEAN DEFAULT FALSE,
    is_verified BOOLEAN DEFAULT FALSE,
    confidence FLOAT DEFAULT 0.0,
    context TEXT,
    frequency INTEGER DEFAULT 0,
    source_lang VARCHAR(10) DEFAULT 'en',
    target_lang VARCHAR(10) DEFAULT 'es',
    embedding vector(1024),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_glossary_term_trgm ON glossary_terms USING gin(term gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_glossary_embedding ON glossary_terms USING ivfflat (embedding vector_cosine_ops);
CREATE INDEX IF NOT EXISTS idx_glossary_entity_type ON glossary_terms(entity_type);
CREATE INDEX IF NOT EXISTS idx_glossary_verified ON glossary_terms(is_verified);
CREATE INDEX IF NOT EXISTS idx_glossary_source_lang ON glossary_terms(source_lang);

CREATE OR REPLACE FUNCTION update_glossary_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS glossary_update_timestamp ON glossary_terms;
CREATE TRIGGER glossary_update_timestamp
    BEFORE UPDATE ON glossary_terms
    FOR EACH ROW
    EXECUTE FUNCTION update_glossary_timestamp();

-- Term contexts
CREATE TABLE IF NOT EXISTS term_contexts (
    id SERIAL PRIMARY KEY,
    term_id INTEGER NOT NULL REFERENCES glossary_terms(id) ON DELETE CASCADE,
    context_hint VARCHAR(200) NOT NULL,
    translation VARCHAR(500) NOT NULL,
    example_usage TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Context examples
CREATE TABLE IF NOT EXISTS context_examples (
    id SERIAL PRIMARY KEY,
    context_id INTEGER NOT NULL REFERENCES term_contexts(id) ON DELETE CASCADE,
    original_sentence TEXT NOT NULL,
    translated_sentence TEXT NOT NULL,
    chapter_id INTEGER REFERENCES chapters(id) ON DELETE SET NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Entity blacklist
CREATE TABLE IF NOT EXISTS entity_blacklist (
    id SERIAL PRIMARY KEY,
    term VARCHAR(200) NOT NULL UNIQUE,
    reason VARCHAR(100),
    created_at TIMESTAMP DEFAULT NOW()
);

INSERT INTO entity_blacklist (term, reason) VALUES
    ('the', 'stopword'), ('and', 'stopword'), ('or', 'stopword'),
    ('but', 'stopword'), ('in', 'stopword'), ('on', 'stopword'),
    ('at', 'stopword'), ('to', 'stopword'), ('for', 'stopword'),
    ('of', 'stopword'), ('a', 'stopword'), ('an', 'stopword'),
    ('is', 'stopword'), ('was', 'stopword'), ('be', 'stopword'),
    ('been', 'stopword'), ('have', 'stopword'), ('had', 'stopword'),
    ('do', 'stopword'), ('did', 'stopword'),
    ('said', 'stopword'), ('asked', 'stopword'), ('replied', 'stopword'),
    ('thought', 'stopword'), ('felt', 'stopword'), ('knew', 'stopword'),
    ('saw', 'stopword'),
    ('chapter', 'metadata'), ('volume', 'metadata'), ('part', 'metadata'),
    ('book', 'metadata'), ('story', 'metadata'), ('novel', 'metadata'),
    ('el', 'stopword'), ('la', 'stopword'), ('los', 'stopword'),
    ('las', 'stopword'), ('un', 'stopword'), ('una', 'stopword'),
    ('de', 'stopword'), ('del', 'stopword'), ('al', 'stopword'),
    ('he', 'stopword'), ('she', 'stopword'), ('it', 'stopword'),
    ('they', 'stopword'), ('we', 'stopword'), ('i', 'stopword'),
    ('you', 'stopword'), ('him', 'stopword'), ('her', 'stopword'),
    ('them', 'stopword'), ('me', 'stopword'), ('us', 'stopword')
ON CONFLICT (term) DO NOTHING;

-- Fantasy terms
CREATE TABLE IF NOT EXISTS fantasy_terms (
    id SERIAL PRIMARY KEY,
    term VARCHAR(200) NOT NULL UNIQUE,
    entity_type VARCHAR(50) NOT NULL,
    do_not_translate BOOLEAN DEFAULT FALSE,
    context_hint VARCHAR(500),
    created_at TIMESTAMP DEFAULT NOW()
);

INSERT INTO fantasy_terms (term, entity_type, do_not_translate, context_hint) VALUES
    ('slime', 'race', TRUE, 'gelatinous creature'),
    ('goblin', 'race', TRUE, 'small malignant creature'),
    ('orc', 'race', TRUE, 'aggressive humanoid creature'),
    ('elf', 'race', TRUE, 'long-lived magical creature'),
    ('dwarf', 'race', TRUE, 'small forging creature'),
    ('dragon', 'race', FALSE, 'colossal winged beast'),
    ('demon', 'race', FALSE, 'infernal creature'),
    ('undead', 'race', TRUE, 'undead creature'),
    ('vampire', 'race', TRUE, 'blood-drinking undead'),
    ('werewolf', 'race', TRUE, 'wolf-man'),
    ('guild', 'organization', FALSE, 'adventurer association'),
    ('sect', 'organization', FALSE, 'martial arts school'),
    ('dungeon', 'place', FALSE, 'labyrinth with monsters'),
    ('labyrinth', 'place', FALSE, 'underground maze'),
    ('mana', 'skill', FALSE, 'magical energy'),
    ('spell', 'spell', FALSE, 'active magic'),
    ('qi', 'skill', TRUE, 'Chinese vital energy'),
    ('cultivation', 'skill', FALSE, 'spiritual practice'),
    ('adventurer', 'title', FALSE, 'explorer profession'),
    ('hero', 'title', FALSE, 'chosen protagonist'),
    ('sage', 'title', FALSE, 'ancient mage')
ON CONFLICT (term) DO NOTHING;

-- Uploaded files (language columns removed, languages live in works)
CREATE TABLE IF NOT EXISTS uploaded_files (
    id SERIAL PRIMARY KEY,
    filename VARCHAR(255) NOT NULL,
    original_name VARCHAR(500) NOT NULL,
    file_path TEXT,
    file_size BIGINT NOT NULL,
    file_type VARCHAR(50) NOT NULL,
    mime_type VARCHAR(100),
    work_id INTEGER REFERENCES works(id) ON DELETE SET NULL,
    volume_id INTEGER REFERENCES volumes(id) ON DELETE SET NULL,
    status VARCHAR(50) DEFAULT 'uploaded',
    error_message TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_uploaded_files_status ON uploaded_files(status);
CREATE INDEX IF NOT EXISTS idx_uploaded_files_work_id ON uploaded_files(work_id);

-- Substitution rules
CREATE TABLE IF NOT EXISTS text_substitution_rules (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    pattern VARCHAR(500) NOT NULL,
    replacement VARCHAR(500) NOT NULL,
    description TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    apply_on_extract BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_substitution_rules_active ON text_substitution_rules(is_active);
CREATE INDEX IF NOT EXISTS idx_substitution_rules_apply ON text_substitution_rules(apply_on_extract);

-- Glossary build progress
CREATE TABLE IF NOT EXISTS glossary_build_progress (
    id SERIAL PRIMARY KEY,
    work_id INTEGER NOT NULL REFERENCES works(id) ON DELETE CASCADE,
    volume_id INTEGER NOT NULL REFERENCES volumes(id) ON DELETE CASCADE,
    entity_text VARCHAR(200) NOT NULL,
    phase VARCHAR(20) NOT NULL DEFAULT 'extracted',
    entity_type VARCHAR(50),
    frequency INTEGER DEFAULT 1,
    contexts TEXT[],
    translation VARCHAR(500),
    embedding vector(1024),
    validation_batch INTEGER,
    translation_batch INTEGER,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_progress_unique_entity ON glossary_build_progress(work_id, volume_id, LOWER(entity_text));
CREATE INDEX IF NOT EXISTS idx_progress_work_volume ON glossary_build_progress(work_id, volume_id);
CREATE INDEX IF NOT EXISTS idx_progress_phase ON glossary_build_progress(phase);
CREATE INDEX IF NOT EXISTS idx_progress_resume ON glossary_build_progress(work_id, volume_id, phase) WHERE phase != 'saved';
CREATE INDEX IF NOT EXISTS idx_progress_pending ON glossary_build_progress(work_id, volume_id) WHERE phase IN ('extracted', 'validated', 'translated');

CREATE OR REPLACE FUNCTION update_glossary_progress_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS update_glossary_progress_updated_at ON glossary_build_progress;
CREATE TRIGGER update_glossary_progress_updated_at
    BEFORE UPDATE ON glossary_build_progress
    FOR EACH ROW
    EXECUTE FUNCTION update_glossary_progress_updated_at();
