-- database/schemas/007_glossary_extensions.sql
-- Extender tabla glossary_terms con campos de NER

ALTER TABLE glossary_terms ADD COLUMN IF NOT EXISTS entity_type VARCHAR(50) DEFAULT 'other';
ALTER TABLE glossary_terms ADD COLUMN IF NOT EXISTS do_not_translate BOOLEAN DEFAULT FALSE;
ALTER TABLE glossary_terms ADD COLUMN IF NOT EXISTS is_verified BOOLEAN DEFAULT FALSE;
ALTER TABLE glossary_terms ADD COLUMN IF NOT EXISTS confidence FLOAT DEFAULT 0.0;
ALTER TABLE glossary_terms ADD COLUMN IF NOT EXISTS source_language VARCHAR(10) DEFAULT 'en';
ALTER TABLE glossary_terms ADD COLUMN IF NOT EXISTS target_language VARCHAR(10) DEFAULT 'es';

-- Índices para los nuevos campos
CREATE INDEX IF NOT EXISTS idx_glossary_entity_type ON glossary_terms(entity_type);
CREATE INDEX IF NOT EXISTS idx_glossary_verified ON glossary_terms(is_verified);
CREATE INDEX IF NOT EXISTS idx_glossary_source_lang ON glossary_terms(source_language);
