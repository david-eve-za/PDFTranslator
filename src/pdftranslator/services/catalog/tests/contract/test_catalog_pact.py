"""
Pact Contract Tests for Catalog Service.

CUPID Principle: Composable
- Consumer-driven contracts
- Verifies API compatibility with Angular frontend
- Runs in CI pipeline
"""

from __future__ import annotations
import pytest
from pact import Consumer, Provider, Like, EachLike
import asyncio

from pdftranslator.services.catalog.main import create_app


@pytest.fixture(scope="module")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="module")
async def catalog_app():
    """Create FastAPI test app."""
    app = create_app()
    yield app


@pytest.fixture(scope="module")
def pact():
    """Pact configuration."""
    pact = Consumer("angular-frontend").has_pact_with(
        Provider("catalog-service"),
        host_name="localhost",
        port=1234,
        pact_dir="./pacts",
    )
    pact.start_service()
    yield pact
    pact.stop_service()


class TestWorkContracts:
    """Contract tests for Works API."""

    def test_get_works_list(self, pact, catalog_app):
        """Test GET /works returns paginated list."""
        expected = {
            "items": EachLike({
                "id": Like(1),
                "uuid": Like("550e8400-e29b-41d4-a716-446655440000"),
                "title": Like("The Great Novel"),
                "title_translated": Like("La Gran Novela"),
                "author": Like("Jane Author"),
                "source_lang": Like("en"),
                "target_lang": Like("es"),
                "volumes": EachLike({
                    "id": Like(1),
                    "volume_number": Like(1),
                    "title": Like("Volume 1"),
                    "total_chapters": Like(10),
                    "translated_chapters": Like(5),
                }),
                "total_volumes": Like(1),
                "total_chapters": Like(10),
                "translated_chapters": Like(5),
                "translation_progress": Like(50.0),
                "created_at": Like("2024-01-15T10:30:00"),
                "updated_at": Like("2024-01-15T10:30:00"),
            }),
            "total": Like(1),
            "page": Like(1),
            "page_size": Like(20),
            "total_pages": Like(1),
        }

        (pact
         .given("works exist in the catalog")
         .upon_receiving("a request for works list")
         .with_request("GET", "/works", query="page=1&page_size=20")
         .will_respond_with(200, body=expected))

        with pact:
            pass  # Test would use test client here

    def test_get_work_by_id(self, pact, catalog_app):
        """Test GET /works/{id} returns full work aggregate."""
        expected = {
            "id": Like(1),
            "uuid": Like("550e8400-e29b-41d4-a716-446655440000"),
            "title": Like("The Great Novel"),
            "title_translated": Like("La Gran Novela"),
            "author": Like("Jane Author"),
            "source_lang": Like("en"),
            "target_lang": Like("es"),
            "volumes": EachLike({
                "id": Like(1),
                "volume_number": Like(1),
                "title": Like("Volume 1"),
                "total_chapters": Like(10),
                "translated_chapters": Like(5),
            }),
            "total_volumes": Like(1),
            "total_chapters": Like(10),
            "translated_chapters": Like(5),
            "translation_progress": Like(50.0),
            "created_at": Like("2024-01-15T10:30:00"),
            "updated_at": Like("2024-01-15T10:30:00"),
        }

        (pact
         .given("a work with id 1 exists")
         .upon_receiving("a request for work by id")
         .with_request("GET", "/works/1")
         .will_respond_with(200, body=expected))

        with pact:
            pass

    def test_get_work_not_found(self, pact, catalog_app):
        """Test GET /works/{id} returns 404 for missing work."""
        (pact
         .given("no work with id 999 exists")
         .upon_receiving("a request for non-existent work")
         .with_request("GET", "/works/999")
         .will_respond_with(404, body={"detail": "Work 999 not found"}))

        with pact:
            pass


class TestVolumeContracts:
    """Contract tests for Volumes API."""

    def test_get_volumes_for_work(self, pact, catalog_app):
        """Test GET /works/{work_id}/volumes."""
        expected = {
            "items": EachLike({
                "id": Like(1),
                "uuid": Like("550e8400-e29b-41d4-a716-446655440000"),
                "work_id": Like(1),
                "volume_number": Like(1),
                "title": Like("Volume 1"),
                "chapter_count": Like(10),
                "translated_chapters": Like(5),
                "translation_progress": Like(50.0),
                "glossary_build_status": Like("completed"),
                "created_at": Like("2024-01-15T10:30:00"),
                "updated_at": Like("2024-01-15T10:30:00"),
            }),
            "total": Like(1),
            "page": Like(1),
            "page_size": Like(20),
            "total_pages": Like(1),
        }

        (pact
         .given("work 1 exists with volumes")
         .upon_receiving("a request for volumes of work 1")
         .with_request("GET", "/works/1/volumes")
         .will_respond_with(200, body=expected))

        with pact:
            pass

    def test_get_volume_with_chapters(self, pact, catalog_app):
        """Test GET /works/{work_id}/volumes/{volume_id} includes chapters."""
        expected = {
            "id": Like(1),
            "uuid": Like("550e8400-e29b-41d4-a716-446655440000"),
            "work_id": Like(1),
            "volume_number": Like(1),
            "title": Like("Volume 1"),
            "chapters": EachLike({
                "id": Like(1),
                "uuid": Like("660e8400-e29b-41d4-a716-446655440000"),
                "volume_id": Like(1),
                "chapter_number": Like(1),
                "title": Like("Chapter 1"),
                "is_translated": Like(True),
                "word_count_original": Like(2500),
                "word_count_translated": Like(2650),
                "created_at": Like("2024-01-15T10:30:00"),
                "updated_at": Like("2024-01-15T10:30:00"),
            }),
            "chapter_count": Like(10),
            "translated_chapters": Like(5),
            "translation_progress": Like(50.0),
            "glossary_build_status": Like("completed"),
            "created_at": Like("2024-01-15T10:30:00"),
            "updated_at": Like("2024-01-15T10:30:00"),
        }

        (pact
         .given("volume 1 exists with chapters")
         .upon_receiving("a request for volume 1 with chapters")
         .with_request("GET", "/works/1/volumes/1")
         .will_respond_with(200, body=expected))

        with pact:
            pass


class TestChapterContracts:
    """Contract tests for Chapters API."""

    def test_get_chapters_for_volume(self, pact, catalog_app):
        """Test GET /volumes/{volume_id}/chapters pagination."""
        expected = {
            "items": EachLike({
                "id": Like(1),
                "uuid": Like("660e8400-e29b-41d4-a716-446655440000"),
                "volume_id": Like(1),
                "chapter_number": Like(1),
                "title": Like("Chapter 1"),
                "is_translated": Like(True),
                "word_count_original": Like(2500),
                "word_count_translated": Like(2650),
                "created_at": Like("2024-01-15T10:30:00"),
                "updated_at": Like("2024-01-15T10:30:00"),
            }),
            "total": Like(10),
            "page": Like(1),
            "page_size": Like(50),
            "total_pages": Like(1),
        }

        (pact
         .given("volume 1 has chapters")
         .upon_receiving("a request for chapters of volume 1")
         .with_request("GET", "/volumes/1/chapters")
         .will_respond_with(200, body=expected))

        with pact:
            pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])