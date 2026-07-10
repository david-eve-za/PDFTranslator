-- ============================================================================
-- PDFTranslator - SQLite Database Schema
-- ============================================================================
-- This script creates the complete database schema for SQLite.
-- All PostgreSQL-specific features have been adapted for SQLite.
-- ============================================================================

-- SQLite doesn't support CREATE EXTENSION
-- We handle GIN/trigram indexes, vector similarity in application layer

-- ============================================================================
-- TABLES
-- ============================================================================

-- Works
CREATE TABLE IF NOT EXISTS works (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title VARCHAR(500) NOT NULL,
    title_translated VARCHAR(500),
    source_lang VARCHAR(10) DEFAULT 'en',
    target_lang VARCHAR(10) DEFAULT 'es',
    author VARCHAR(300),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create index for title search (will use LIKE in SQLite)
CREATE INDEX IF NOT EXISTS idx_works_title ON works(title);

-- Volumes (includes glossary tracking)
CREATE TABLE IF NOT EXISTS volumes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    work_id INTEGER NOT NULL REFERENCES works(id) ON DELETE CASCADE,
    volume_number INTEGER NOT NULL,
    title VARCHAR(500),
    full_text TEXT,
    translated_text TEXT,
    glossary_built_at TIMESTAMP,
    glossary_build_status VARCHAR(20) DEFAULT 'pending',
    glossary_error_message TEXT,
    glossary_resume_phase VARCHAR(20),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT unique_work_volume UNIQUE(work_id, volume_number)
);

CREATE INDEX IF NOT EXISTS idx_volumes_work_id ON volumes(work_id);
CREATE INDEX IF NOT EXISTS idx_volumes_build_status ON volumes(glossary_build_status);

-- Chapters (chapter_number nullable for Prologue/Epilogue)
CREATE TABLE IF NOT EXISTS chapters (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    volume_id INTEGER NOT NULL REFERENCES volumes(id) ON DELETE CASCADE,
    chapter_number INTEGER,
    title VARCHAR(500),
    start_position INTEGER,
    end_position INTEGER,
    original_text TEXT,
    translated_text TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Unique constraint for numbered chapters within a volume
CREATE UNIQUE INDEX IF NOT EXISTS idx_unique_volume_chapter ON chapters(volume_id, chapter_number) WHERE chapter_number IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_chapters_volume_id ON chapters(volume_id);

-- Glossary terms (includes NER fields)
CREATE TABLE IF NOT EXISTS glossary_terms (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    work_id INTEGER NOT NULL REFERENCES works(id) ON DELETE CASCADE,
    term VARCHAR(200) NOT NULL,
    translation VARCHAR(500),
    notes TEXT,
    is_proper_noun BOOLEAN DEFAULT FALSE,
    entity_type VARCHAR(50) DEFAULT 'other',
    do_not_translate BOOLEAN DEFAULT FALSE,
    is_verified BOOLEAN DEFAULT FALSE,
    confidence REAL DEFAULT 0.0,
    context TEXT,
    frequency INTEGER DEFAULT 0,
    source_lang VARCHAR(10) DEFAULT 'en',
    target_lang VARCHAR(10) DEFAULT 'es',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_glossary_term ON glossary_terms(term);
CREATE INDEX IF NOT EXISTS idx_glossary_work_id ON glossary_terms(work_id);
CREATE INDEX IF NOT EXISTS idx_glossary_entity_type ON glossary_terms(entity_type);
CREATE INDEX IF NOT EXISTS idx_glossary_verified ON glossary_terms(is_verified);
CREATE INDEX IF NOT EXISTS idx_glossary_source_lang ON glossary_terms(source_lang);

-- Trigger to update updated_at on glossary_terms
CREATE TRIGGER IF NOT EXISTS glossary_update_timestamp
    AFTER UPDATE ON glossary_terms
BEGIN
    UPDATE glossary_terms SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

-- Term contexts
CREATE TABLE IF NOT EXISTS term_contexts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    term_id INTEGER NOT NULL REFERENCES glossary_terms(id) ON DELETE CASCADE,
    context_hint VARCHAR(200) NOT NULL,
    translation VARCHAR(500) NOT NULL,
    example_usage TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_term_contexts_term_id ON term_contexts(term_id);

-- Context examples
CREATE TABLE IF NOT EXISTS context_examples (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    context_id INTEGER NOT NULL REFERENCES term_contexts(id) ON DELETE CASCADE,
    original_sentence TEXT NOT NULL,
    translated_sentence TEXT NOT NULL,
    chapter_id INTEGER REFERENCES chapters(id) ON DELETE SET NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_context_examples_context_id ON context_examples(context_id);
CREATE INDEX IF NOT EXISTS idx_context_examples_chapter_id ON context_examples(chapter_id);

-- Entity blacklist
CREATE TABLE IF NOT EXISTS entity_blacklist (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    term VARCHAR(200) NOT NULL UNIQUE,
    reason VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Fantasy terms
CREATE TABLE IF NOT EXISTS fantasy_terms (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    term VARCHAR(200) NOT NULL UNIQUE,
    entity_type VARCHAR(50) NOT NULL,
    do_not_translate BOOLEAN DEFAULT FALSE,
    context_hint VARCHAR(500),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Seed entity blacklist
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

-- Seed fantasy terms
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
    id INTEGER PRIMARY KEY AUTOINCREMENT,
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
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_uploaded_files_status ON uploaded_files(status);
CREATE INDEX IF NOT EXISTS idx_uploaded_files_work_id ON uploaded_files(work_id);

-- Trigger for uploaded_files updated_at
CREATE TRIGGER IF NOT EXISTS uploaded_files_update_timestamp
    AFTER UPDATE ON uploaded_files
BEGIN
    UPDATE uploaded_files SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

-- Substitution rules
CREATE TABLE IF NOT EXISTS text_substitution_rules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(100) NOT NULL,
    pattern VARCHAR(500) NOT NULL,
    replacement VARCHAR(500) NOT NULL,
    description TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    apply_on_extract BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_substitution_rules_active ON text_substitution_rules(is_active);
CREATE INDEX IF NOT EXISTS idx_substitution_rules_apply ON text_substitution_rules(apply_on_extract);

-- Trigger for substitution_rules updated_at
CREATE TRIGGER IF NOT EXISTS substitution_rules_update_timestamp
    AFTER UPDATE ON text_substitution_rules
BEGIN
    UPDATE text_substitution_rules SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

-- Glossary build progress
CREATE TABLE IF NOT EXISTS glossary_build_progress (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    work_id INTEGER NOT NULL REFERENCES works(id) ON DELETE CASCADE,
    volume_id INTEGER NOT NULL REFERENCES volumes(id) ON DELETE CASCADE,
    entity_text VARCHAR(200) NOT NULL,
    phase VARCHAR(20) NOT NULL DEFAULT 'extracted',
    entity_type VARCHAR(50),
    frequency INTEGER DEFAULT 1,
    contexts TEXT,  -- JSON array of strings
    translation VARCHAR(500),
    validation_batch INTEGER,
    translation_batch INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_progress_unique_entity ON glossary_build_progress(work_id, volume_id, LOWER(entity_text));
CREATE INDEX IF NOT EXISTS idx_progress_work_volume ON glossary_build_progress(work_id, volume_id);
CREATE INDEX IF NOT EXISTS idx_progress_phase ON glossary_build_progress(phase);
CREATE INDEX IF NOT EXISTS idx_progress_resume ON glossary_build_progress(work_id, volume_id, phase) WHERE phase != 'saved';
CREATE INDEX IF NOT EXISTS idx_progress_pending ON glossary_build_progress(work_id, volume_id) WHERE phase IN ('extracted', 'validated', 'translated');

-- Trigger for glossary_build_progress updated_at
CREATE TRIGGER IF NOT EXISTS glossary_progress_update_timestamp
    AFTER UPDATE ON glossary_build_progress
BEGIN
    UPDATE glossary_build_progress SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

-- Translation jobs
CREATE TABLE IF NOT EXISTS translation_jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
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
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_translation_jobs_work_id ON translation_jobs(work_id);
CREATE INDEX IF NOT EXISTS idx_translation_jobs_status ON translation_jobs(status);

-- Trigger for translation_jobs updated_at
CREATE TRIGGER IF NOT EXISTS translation_jobs_update_timestamp
    AFTER UPDATE ON translation_jobs
BEGIN
    UPDATE translation_jobs SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;