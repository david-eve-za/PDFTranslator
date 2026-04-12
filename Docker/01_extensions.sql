-- Ejecutado automáticamente al crear la base de datos
-- Habilitar pgvector para embeddings semánticos
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;    -- Búsqueda fuzzy de términos
CREATE EXTENSION IF NOT EXISTS "uuid-ossp"; -- UUIDs nativos

-- Verificar instalación
DO $$
BEGIN
  RAISE NOTICE 'pgvector version: %', (SELECT extversion FROM pg_extension WHERE extname = 'vector');
END $$;
