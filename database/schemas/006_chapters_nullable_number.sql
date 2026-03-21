-- database/schemas/006_chapters_nullable_number.sql
-- Make chapter_number nullable to support Prologue/Epilogue (no chapter number)

-- Remove the unique constraint that includes chapter_number
ALTER TABLE chapters DROP CONSTRAINT IF EXISTS unique_volume_chapter;

-- Make chapter_number nullable
ALTER TABLE chapters ALTER COLUMN chapter_number DROP NOT NULL;

-- Add new unique constraint that allows multiple NULL chapter_numbers per volume
-- PostgreSQL UNIQUE constraint allows multiple NULLs, so this works for Prologue/Epilogue
CREATE UNIQUE INDEX idx_unique_volume_chapter ON chapters(volume_id, chapter_number) 
WHERE chapter_number IS NOT NULL;
