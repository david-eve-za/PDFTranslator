-- Add glossary_built_at column to volumes table
ALTER TABLE volumes ADD COLUMN IF NOT EXISTS glossary_built_at TIMESTAMP;

-- Create index for faster lookups
CREATE INDEX IF NOT EXISTS idx_volumes_glossary_built ON volumes(glossary_built_at) WHERE glossary_built_at IS NOT NULL;
