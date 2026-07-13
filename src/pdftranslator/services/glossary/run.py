"""
Glossary Service Entry Point Runner.

CUPID Principle: Predictable
- Explicit initialization order
- Clear error messages
- Single entry point for service startup
"""

from __future__ import annotations
import asyncio
import logging
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from src.pdftranslator.services.glossary.config import get_glossary_settings
from src.pdftranslator.services.glossary.infrastructure.database.connection import DatabaseConnection

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def run_migrations() -> None:
    """Run database migrations."""
    settings = get_glossary_settings()
    logger.info(f"Running migrations on: {settings.database_path}")

    db = DatabaseConnection(settings)
    await db.connect()
    try:
        # Use the actual pool connection for migrations
        async with db.connection() as conn:
            from src.pdftranslator.services.glossary.infrastructure.database.migrations import run_migrations
            await run_migrations(conn)
        logger.info("Migrations completed successfully")
    finally:
        await db.close()


async def start_service() -> None:
    """Start the FastAPI service."""
    import uvicorn

    settings = get_glossary_settings()
    logger.info(f"Starting service on {settings.host}:{settings.port}")

    await uvicorn.Server(
        uvicorn.Config(
            "src.pdftranslator.services.glossary.main:app",
            host=settings.host,
            port=settings.port,
            workers=settings.workers,
            log_level=settings.log_level.lower(),
        )
    ).serve()


def main() -> None:
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Glossary Service Runner")
    parser.add_argument(
        "command",
        choices=["migrate", "serve"],
        help="Command to run",
    )
    args = parser.parse_args()

    if args.command == "migrate":
        asyncio.run(run_migrations())
    elif args.command == "serve":
        asyncio.run(start_service())
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()