"""
Database Migrations for Glossary Service.

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
            # Works table
            """
            CREATE TABLE IF NOT EXISTS works (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title VARCHAR(500) NOT NULL,
                title_translated VARCHAR(500),
                source_lang VARCHAR(10) DEFAULT 'en',
                target_lang VARCHAR(10) DEFAULT 'es',
                author VARCHAR(300),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            "CREATE INDEX IF NOT EXISTS idx_works_title ON works(title)",

            # Volumes table
            """
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
            )
            """,
            "CREATE INDEX IF NOT EXISTS idx_volumes_work_id ON volumes(work_id)",
            "CREATE INDEX IF NOT EXISTS idx_volumes_build_status ON volumes(glossary_build_status)",

            # Chapters table
            """
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
            )
            """,
            """
            CREATE UNIQUE INDEX IF NOT EXISTS idx_unique_volume_chapter
            ON chapters(volume_id, chapter_number) WHERE chapter_number IS NOT NULL
            """,
            "CREATE INDEX IF NOT EXISTS idx_chapters_volume_id ON chapters(volume_id)",

            # Glossaries table
            """
            CREATE TABLE IF NOT EXISTS glossaries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                work_id INTEGER NOT NULL REFERENCES works(id) ON DELETE CASCADE,
                name VARCHAR(200) NOT NULL,
                source_lang VARCHAR(10) DEFAULT 'en',
                target_lang VARCHAR(10) DEFAULT 'es',
                status VARCHAR(20) DEFAULT 'draft',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                CONSTRAINT unique_work_glossary UNIQUE(work_id, source_lang, target_lang)
            )
            """,

            # Glossary entries (terms)
            """
            CREATE TABLE IF NOT EXISTS glossary_entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                glossary_id INTEGER NOT NULL REFERENCES glossaries(id) ON DELETE CASCADE,
                term VARCHAR(200) NOT NULL,
                translation VARCHAR(500),
                entity_type VARCHAR(50) DEFAULT 'other',
                is_proper_noun BOOLEAN DEFAULT FALSE,
                do_not_translate BOOLEAN DEFAULT FALSE,
                is_verified BOOLEAN DEFAULT FALSE,
                confidence REAL DEFAULT 0.0,
                frequency INTEGER DEFAULT 1,
                context TEXT,
                notes TEXT,
                source_lang VARCHAR(10) DEFAULT 'en',
                target_lang VARCHAR(10) DEFAULT 'es',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            "CREATE INDEX IF NOT EXISTS idx_glossary_entries_glossary_id ON glossary_entries(glossary_id)",
            "CREATE INDEX IF NOT EXISTS idx_glossary_entries_term ON glossary_entries(term)",
            "CREATE INDEX IF NOT EXISTS idx_glossary_entries_entity_type ON glossary_entries(entity_type)",
            "CREATE INDEX IF NOT EXISTS idx_glossary_entries_verified ON glossary_entries(is_verified)",
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_glossary_entries_unique_term ON glossary_entries(glossary_id, LOWER(term))",

            # Build pipelines table
            """
            CREATE TABLE IF NOT EXISTS build_pipelines (
                id TEXT PRIMARY KEY,  -- UUID
                work_id INTEGER NOT NULL REFERENCES works(id) ON DELETE CASCADE,
                volume_id INTEGER NOT NULL REFERENCES volumes(id) ON DELETE CASCADE,
                source_lang VARCHAR(10) DEFAULT 'en',
                target_lang VARCHAR(10) DEFAULT 'es',
                min_frequency INTEGER DEFAULT 2,
                dry_run BOOLEAN DEFAULT FALSE,
                status VARCHAR(20) DEFAULT 'pending',
                current_stage INTEGER DEFAULT 0,
                filtered_count INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            "CREATE INDEX IF NOT EXISTS idx_build_pipelines_work_volume ON build_pipelines(work_id, volume_id)",
            "CREATE INDEX IF NOT EXISTS idx_build_pipelines_status ON build_pipelines(status)",

            # Pipeline stages table
            """
            CREATE TABLE IF NOT EXISTS pipeline_stages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pipeline_id TEXT NOT NULL REFERENCES build_pipelines(id) ON DELETE CASCADE,
                name VARCHAR(20) NOT NULL,
                status VARCHAR(20) DEFAULT 'pending',
                input_data TEXT,  -- JSON
                output_data TEXT,  -- JSON
                error_message TEXT,
                started_at TIMESTAMP,
                completed_at TIMESTAMP,
                retry_count INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                CONSTRAINT unique_pipeline_stage UNIQUE(pipeline_id, name)
            )
            """,
            "CREATE INDEX IF NOT EXISTS idx_pipeline_stages_pipeline_id ON pipeline_stages(pipeline_id)",

            # Entity blacklist
            """
            CREATE TABLE IF NOT EXISTS entity_blacklist (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                term VARCHAR(200) NOT NULL UNIQUE,
                reason VARCHAR(100),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,

            # Fantasy terms
            """
            CREATE TABLE IF NOT EXISTS fantasy_terms (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                term VARCHAR(200) NOT NULL UNIQUE,
                entity_type VARCHAR(50) NOT NULL,
                do_not_translate BOOLEAN DEFAULT FALSE,
                context_hint VARCHAR(500),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,

            # Entity candidates (for progress tracking during build)
            """
            CREATE TABLE IF NOT EXISTS entity_candidates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pipeline_id TEXT NOT NULL REFERENCES build_pipelines(id) ON DELETE CASCADE,
                entity_text VARCHAR(200) NOT NULL,
                entity_type VARCHAR(50),
                frequency INTEGER DEFAULT 1,
                contexts TEXT,  -- JSON array
                confidence REAL DEFAULT 0.0,
                validated BOOLEAN DEFAULT FALSE,
                translation VARCHAR(500),
                embedding BLOB,  -- serialized numpy array
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            "CREATE INDEX IF NOT EXISTS idx_entity_candidates_pipeline ON entity_candidates(pipeline_id)",

            # Triggers for updated_at
            """
            CREATE TRIGGER IF NOT EXISTS glossaries_update_timestamp
            AFTER UPDATE ON glossaries
            BEGIN
                UPDATE glossaries SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
            END
            """,
            """
            CREATE TRIGGER IF NOT EXISTS glossary_entries_update_timestamp
            AFTER UPDATE ON glossary_entries
            BEGIN
                UPDATE glossary_entries SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
            END
            """,
            """
            CREATE TRIGGER IF NOT EXISTS build_pipelines_update_timestamp
            AFTER UPDATE ON build_pipelines
            BEGIN
                UPDATE build_pipelines SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
            END
            """,
            """
            CREATE TRIGGER IF NOT EXISTS pipeline_stages_update_timestamp
            AFTER UPDATE ON pipeline_stages
            BEGIN
                UPDATE pipeline_stages SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
            END
            """,
        ],
    ),

    Migration(
        name="002_seed_data",
        statements=[
            # Seed entity blacklist
            """
            INSERT OR IGNORE INTO entity_blacklist (term, reason) VALUES
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
            """,

            # Seed fantasy terms
            """
            INSERT OR IGNORE INTO fantasy_terms (term, entity_type, do_not_translate, context_hint) VALUES
            ('slime', 'race', 1, 'gelatinous creature'),
            ('goblin', 'race', 1, 'small malignant creature'),
            ('orc', 'race', 1, 'aggressive humanoid creature'),
            ('elf', 'race', 1, 'long-lived magical creature'),
            ('dwarf', 'race', 1, 'small forging creature'),
            ('dragon', 'race', 0, 'colossal winged beast'),
            ('demon', 'race', 0, 'infernal creature'),
            ('undead', 'race', 1, 'undead creature'),
            ('vampire', 'race', 1, 'blood-drinking undead'),
            ('werewolf', 'race', 1, 'wolf-man'),
            ('guild', 'organization', 0, 'adventurer association'),
            ('sect', 'organization', 0, 'martial arts school'),
            ('dungeon', 'place', 0, 'labyrinth with monsters'),
            ('labyrinth', 'place', 0, 'underground maze'),
            ('mana', 'skill', 0, 'magical energy'),
            ('spell', 'skill', 0, 'active magic'),
            ('qi', 'skill', 1, 'Chinese vital energy'),
            ('cultivation', 'skill', 0, 'spiritual practice'),
            ('adventurer', 'title', 0, 'explorer profession'),
            ('hero', 'title', 0, 'chosen protagonist'),
            ('sage', 'title', 0, 'ancient mage')
            """,
        ],
    ),
]


# ============================================================================
# MIGRATION RUNNER
# ============================================================================

async def run_migrations(db: aiosqlite.Connection) -> None:
    """Run all pending migrations on the database connection."""
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