"""
Translation Service Database Migrations Package.

CUPID Principle: Predictable
- Explicit versioned migrations
- Idempotent statements
- SQLite-compatible DDL
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import List

import aiosqlite


@dataclass(frozen=True)
class Migration:
    """Single database migration."""

    name: str
    statements: List[str]


# ============================================================================
# MIGRATIONS - Add new migrations to the end of this list
# ============================================================================

MIGRATIONS: List[Migration] = [
    Migration(
        name="001_initial_schema",
        statements=[
            # Translation Jobs table
            """
            CREATE TABLE IF NOT EXISTS translation_jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                uuid TEXT NOT NULL UNIQUE,
                source_lang TEXT NOT NULL CHECK(length(source_lang) = 2),
                target_lang TEXT NOT NULL CHECK(length(target_lang) = 2),
                work_id INTEGER NOT NULL,
                volume_id INTEGER,
                status TEXT NOT NULL DEFAULT 'pending' CHECK(status IN ('pending', 'queued', 'in_progress', 'completed', 'failed', 'paused', 'cancelled')),
                priority INTEGER NOT NULL DEFAULT 50,
                source_text TEXT,
                target_text TEXT,
                llm_provider TEXT,
                model_name TEXT,
                error_message TEXT,
                started_at TEXT,
                completed_at TEXT,
                glossary_refs TEXT NOT NULL DEFAULT '[]',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                CHECK (source_lang != target_lang)
            )
            """,
            "CREATE INDEX IF NOT EXISTS idx_translation_jobs_work_id ON translation_jobs(work_id)",
            "CREATE INDEX IF NOT EXISTS idx_translation_jobs_status ON translation_jobs(status)",
            "CREATE INDEX IF NOT EXISTS idx_translation_jobs_uuid ON translation_jobs(uuid)",
            "CREATE INDEX IF NOT EXISTS idx_translation_jobs_created_at ON translation_jobs(created_at)",

            # Translation Segments table
            """
            CREATE TABLE IF NOT EXISTS translation_segments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                uuid TEXT NOT NULL UNIQUE,
                job_id INTEGER NOT NULL REFERENCES translation_jobs(id) ON DELETE CASCADE,
                segment_number INTEGER CHECK(segment_number > 0),
                source_text TEXT,
                target_text TEXT,
                context_before TEXT,
                context_after TEXT,
                notes TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(job_id, segment_number)
            )
            """,
            "CREATE INDEX IF NOT EXISTS idx_translation_segments_job_id ON translation_segments(job_id)",
            "CREATE INDEX IF NOT EXISTS idx_translation_segments_uuid ON translation_segments(uuid)",

            # Pipeline Stages table (for tracking translation pipeline progress)
            """
            CREATE TABLE IF NOT EXISTS translation_pipelines (
                id TEXT PRIMARY KEY,  -- UUID
                job_id INTEGER NOT NULL REFERENCES translation_jobs(id) ON DELETE CASCADE,
                source_lang TEXT NOT NULL CHECK(length(source_lang) = 2),
                target_lang TEXT NOT NULL CHECK(length(target_lang) = 2),
                work_id INTEGER NOT NULL,
                volume_id INTEGER,
                status TEXT NOT NULL DEFAULT 'pending' CHECK(status IN ('pending', 'running', 'completed', 'failed', 'paused', 'cancelled')),
                current_stage INTEGER DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """,
            "CREATE INDEX IF NOT EXISTS idx_translation_pipelines_job_id ON translation_pipelines(job_id)",
            "CREATE INDEX IF NOT EXISTS idx_translation_pipelines_status ON translation_pipelines(status)",

            # Pipeline Stages table
            """
            CREATE TABLE IF NOT EXISTS translation_pipeline_stages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pipeline_id TEXT NOT NULL REFERENCES translation_pipelines(id) ON DELETE CASCADE,
                name TEXT NOT NULL CHECK(name IN ('detect', 'segment', 'translate', 'quality_check', 'store')),
                status TEXT NOT NULL DEFAULT 'pending' CHECK(status IN ('pending', 'running', 'completed', 'failed', 'skipped')),
                input_data TEXT,  -- JSON
                output_data TEXT,  -- JSON
                error_message TEXT,
                started_at TEXT,
                completed_at TEXT,
                retry_count INTEGER DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                CONSTRAINT unique_pipeline_stage UNIQUE(pipeline_id, name)
            )
            """,
            "CREATE INDEX IF NOT EXISTS idx_pipeline_stages_pipeline_id ON translation_pipeline_stages(pipeline_id)",

            # Triggers for updated_at
            """
            CREATE TRIGGER IF NOT EXISTS translation_jobs_update_timestamp
            AFTER UPDATE ON translation_jobs
            BEGIN
                UPDATE translation_jobs SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
            END
            """,
            """
            CREATE TRIGGER IF NOT EXISTS translation_segments_update_timestamp
            AFTER UPDATE ON translation_segments
            BEGIN
                UPDATE translation_segments SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
            END
            """,
            """
            CREATE TRIGGER IF NOT EXISTS translation_pipelines_update_timestamp
            AFTER UPDATE ON translation_pipelines
            BEGIN
                UPDATE translation_pipelines SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
            END
            """,
            """
            CREATE TRIGGER IF NOT EXISTS translation_pipeline_stages_update_timestamp
            AFTER UPDATE ON translation_pipeline_stages
            BEGIN
                UPDATE translation_pipeline_stages SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
            END
            """,
        ],
    ),
]


# ============================================================================
# STANDALONE MIGRATION RUNNER
# ============================================================================

async def run_migrations(db: aiosqlite.Connection) -> None:
    """
    Run pending migrations on the given database connection.

    Args:
        db: Connected aiosqlite.Connection with row_factory set
    """
    # Create migrations table
    await db.execute("""
        CREATE TABLE IF NOT EXISTS _migrations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name VARCHAR(255) NOT NULL UNIQUE,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Get applied migrations
    cursor = await db.execute("SELECT name FROM _migrations")
    applied = {row[0] for row in await cursor.fetchall()}

    # Apply pending migrations
    for migration in MIGRATIONS:
        if migration.name not in applied:
            print(f"Applying migration: {migration.name}")
            for statement in migration.statements:
                await db.execute(statement)
            await db.execute(
                "INSERT INTO _migrations (name) VALUES (?)",
                (migration.name,),
            )
            await db.commit()