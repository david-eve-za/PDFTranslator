"""
Translation Service Entry Point Runner.

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

from src.pdftranslator.services.translation.config.settings import TranslationSettings
from src.pdftranslator.services.translation.infrastructure.database.connection import DatabaseConnection

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def run_migrations() -> None:
    """Run database migrations."""
    settings = TranslationSettings()
    db = DatabaseConnection(settings)
    await db.connect()
    try:
        # Use the actual pool connection for migrations
        async with db.connection() as conn:
            from src.pdftranslator.services.translation.infrastructure.database.migrations import run_migrations as run_actual_migrations
            await run_actual_migrations(conn)
        logger.info("Migrations completed successfully")
    finally:
        await db.disconnect()


async def start_service() -> None:
    """Start the FastAPI service."""
    import uvicorn

    settings = TranslationSettings()
    logger.info(f"Starting service on {settings.host}:{settings.port}")

    config = uvicorn.Config(
        "src.pdftranslator.services.translation.main:app",
        host=settings.host,
        port=settings.port,
        workers=settings.workers,
        log_level=settings.log_level.lower(),
    )
    server = uvicorn.Server(config)
    try:
        await server.serve()
    except KeyboardInterrupt:
        logger.info("Shutdown signal received")


def main() -> None:
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Translation Service Runner")
    parser.add_argument(
        "command",
        choices=["migrate", "serve"],
        help="Command to run",
    )
    args = parser.parse_args()

    if args.command == "migrate":
        asyncio.run(run_migrations())
    elif args.command == "serve":
        try:
            asyncio.run(start_service())
        except KeyboardInterrupt:
            pass  # Suppressed - logged in start_service
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()