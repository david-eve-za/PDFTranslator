-- database/schemas/011_glossary_frontend_compat.sql
-- Actualizar tabla glossary_terms para compatibilidad con frontend

-- Agregar columna context si no existe (renamed from notes)
ALTER TABLE glossary_terms ADD COLUMN IF NOT EXISTS context TEXT;

-- Copiar datos de notes a context si context está vacío
UPDATE glossary_terms SET context = notes WHERE context IS NULL AND notes IS NOT NULL;

-- Agregar columna frequency
ALTER TABLE glossary_terms ADD COLUMN IF NOT EXISTS frequency INTEGER DEFAULT 0;

-- Agregar columna updated_at
ALTER TABLE glossary_terms ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT NOW();

-- Renombrar source_language a source_lang si existe
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'glossary_terms' AND column_name = 'source_language') THEN
        ALTER TABLE glossary_terms RENAME COLUMN source_language TO source_lang;
    END IF;
END $$;

-- Renombrar target_language a target_lang si existe
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'glossary_terms' AND column_name = 'target_language') THEN
        ALTER TABLE glossary_terms RENAME COLUMN target_language TO target_lang;
    END IF;
END $$;

-- Asegurar que source_lang y target_lang existen
ALTER TABLE glossary_terms ADD COLUMN IF NOT EXISTS source_lang VARCHAR(10) DEFAULT 'en';
ALTER TABLE glossary_terms ADD COLUMN IF NOT EXISTS target_lang VARCHAR(10) DEFAULT 'es';

-- Agregar columna entity_type si no existe
ALTER TABLE glossary_terms ADD COLUMN IF NOT EXISTS entity_type VARCHAR(50) DEFAULT 'other';

-- Actualizar updated_at al crear/modificar
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
