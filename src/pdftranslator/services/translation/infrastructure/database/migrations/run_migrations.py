#!/usr/bin/env python3
"""
Translation Service Database Migration Runner.

Runs all pending migrations for the translation service database.

Usage:
    python -m pdftranslator.services.translation.infrastructure.database.migrations
"""

from __future__ import annotations
import asyncio
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(PROJECT_ROOT))

from src.pdftranslator.services.translation.infrastructure.database.migrations import run_migrations
from src.pdftranslator.services.translation.config.settings import TranslationSettings


async def main() -> int:
    """Run all pending migrations."""
    settings = TranslationSettings()
    db_path = settings.database_path
    migrations_dir = Path(__file__).parent

    print(f"Running translations migrations...")
    print(f"Database: {db_path}")
    print(f"Migrations dir: {migrations_dir}")

    try:
        await run_migrations(db_path, migrations_dir)
        print("Migrations completed successfully!")
        return 0
    except Exception as e:
        print(f"Migration failed: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))