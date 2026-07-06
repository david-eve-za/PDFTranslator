"""Test configuration and fixtures."""

import os
import pytest
from fastapi.testclient import TestClient
from pdftranslator.backend.main import app
from pdftranslator.database.connection import DatabasePool

# Set test environment variables before importing app
os.environ.setdefault("DB_HOST", "localhost")
os.environ.setdefault("DB_PORT", "5432")
os.environ.setdefault("DB_NAME", "book_translator")
os.environ.setdefault("DB_USER", "translator_user")
os.environ.setdefault("DB_PASSWORD", "testpassword123")


@pytest.fixture(scope="session")
def db_pool():
    """Create and manage database connection pool for the test session."""
    # Reset any existing instance
    DatabasePool.reset_instance()
    
    pool = DatabasePool.get_instance(
        host="localhost",
        port=5432,
        database="book_translator",
        user="translator_user",
        password="testpassword123",
        min_size=1,
        max_size=5,
    )
    
    # Ensure tables exist
    sync_pool = pool.get_sync_pool()
    
    yield pool
    
    # Cleanup
    import asyncio
    try:
        asyncio.run(pool.close())
    except RuntimeError:
        # If we can't run async, just close sync
        if pool._sync_pool:
            pool._sync_pool.close()
            pool._sync_pool = None
    DatabasePool.reset_instance()


@pytest.fixture(scope="function")
def client(db_pool):
    """Create a test client with the database pool."""
    with TestClient(app) as client:
        yield client


@pytest.fixture(scope="function")
def db_sync_pool(db_pool):
    """Get the sync pool for direct database operations in tests."""
    return db_pool.get_sync_pool()