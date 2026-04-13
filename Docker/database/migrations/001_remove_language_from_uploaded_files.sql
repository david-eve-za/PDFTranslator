-- Migration: Remove language columns from uploaded_files table
-- Date: 2025-04-12
-- Description: Languages are now configured in Work entity, not in UploadedFile

-- Drop columns if they exist
ALTER TABLE uploaded_files DROP COLUMN IF EXISTS source_lang;
ALTER TABLE uploaded_files DROP COLUMN IF EXISTS target_lang;

-- Note: This migration is safe to run multiple times (IF EXISTS)
