"""
Pytest configuration for Glossary Service tests.
"""

import asyncio
import os
import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from httpx import AsyncClient

from src.pdftranslator.services.glossary.config import GlossarySettings
from src.pdftranslator.services.glossary.infrastructure.database.connection import DatabaseConnection
from src.pdftranslator.services.glossary.infrastructure.database.migrations import run_migrations
from src.pdftranslator.services.glossary.main import create_app


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def test_settings() -> GlossarySettings:
    """Test settings with in-memory database."""
    return GlossarySettings(
        database_path=":memory:",
        host="0.0.0.0",
        port=8003,
        log_level="DEBUG",
    )


@pytest_asyncio.fixture
async def test_db(test_settings) -> DatabaseConnection:
    """Create test database connection with migrations."""
    db = DatabaseConnection(test_settings)
    await db.connect()
    await run_migrations(db)
    yield db
    await db.close()


@pytest.fixture
def app(test_settings):
    """Create FastAPI app with test settings."""
    from fastapi import Depends
    from src.pdftranslator.services.glossary.api.dependencies import get_settings

    test_app = create_app()
    test_app.dependency_overrides[get_settings] = lambda: test_settings
    return test_app


@pytest.fixture
def client(app) -> TestClient:
    """Sync test client."""
    return TestClient(app)


@pytest_asyncio.fixture
async def async_client(app) -> AsyncClient:
    """Async test client."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


# Test data fixtures
@pytest.fixture
def sample_glossary_data():
    """Sample glossary create data."""
    return {
        "work_id": 1,
        "name": "Test Glossary",
        "source_lang": "en",
        "target_lang": "es",
    }


@pytest.fixture
def sample_build_request():
    """Sample build glossary request."""
    return {
        "work_id": 1,
        "volume_id": 1,
        "text": "The slime attacked the goblin with a mana spell.",
        "source_lang": "en",
        "target_lang": "es",
        "min_frequency": 1,
    }


@pytest.fixture
def sample_entities():
    """Sample entities for stage testing."""
    return [
        {"id": "1", "text": "slime", "entity_type": "race", "frequency": 3, "source_language": "en"},
        {"id": "2", "text": "goblin", "entity_type": "race", "frequency": 2, "source_language": "en"},
        {"id": "3", "text": "mana", "entity_type": "skill", "frequency": 1, "source_language": "en"},
    ]