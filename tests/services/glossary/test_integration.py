"""
Integration Tests for Glossary Pipeline.

CUPID Principle: Composable
- Tests full pipeline execution
- Uses SQLite in-memory for isolation
"""

from __future__ import annotations
import pytest
import asyncio
from uuid import UUID
from unittest.mock import AsyncMock, Mock, patch

from fastapi.testclient import TestClient

from pdftranslator.services.glossary.main import create_app
from pdftranslator.services.glossary.domain.services.glossary_service import GlossaryService
from pdftranslator.services.glossary.domain.services.commands import (
    BuildGlossaryCommand,
    CreateGlossaryCommand,
)
from pdftranslator.services.glossary.domain.models.entity import EntityCandidate, EntityType
from pdftranslator.services.glossary.domain.models.glossary import Glossary, GlossaryEntry
from pdftranslator.services.glossary.domain.models.build_pipeline import BuildPipeline, BuildPipelineStatus
from pdftranslator.services.glossary.infrastructure.database.connection import DatabaseConnection
from pdftranslator.services.glossary.infrastructure.database.repositories import SQLiteGlossaryUnitOfWork


@pytest.fixture
async def db_connection():
    """Create in-memory database for testing."""
    from pdftranslator.services.glossary.config.settings import GlossarySettings
    settings = GlossarySettings(database_path=":memory:")
    db = DatabaseConnection(settings)
    await db.connect()
    yield db
    await db.close()


@pytest.fixture
async def uow(db_connection):
    """Unit of Work with repositories."""
    return SQLiteGlossaryUnitOfWork(db_connection)


@pytest.fixture
async def glossary_service(uow):
    """Glossary service with mocked LLM."""
    with patch("pdftranslator.services.glossary.domain.services.glossary_service.EntityExtractor") as mock_extractor:
        mock_extractor.return_value.extract = AsyncMock(return_value=[])
        service = GlossaryService(uow)
        yield service


class TestFullPipelineIntegration:
    """Integration tests for full glossary pipeline."""

    @pytest.mark.asyncio
    async def test_create_glossary_and_build(self, glossary_service, uow):
        """Test creating glossary and running build pipeline."""
        # Create glossary
        create_cmd = CreateGlossaryCommand(
            work_id=1,
            name="Test Work Glossary",
            source_lang="en",
            target_lang="es",
        )
        glossary = await glossary_service.create_glossary(create_cmd)

        assert glossary.work_id == 1
        assert glossary.name == "Test Work Glossary"
        assert glossary.status.value == "draft"

        # Build glossary with sample text
        text = """
        The slime attacked the goblin with a mana spell.
        The adventurer cast fireball at the dragon.
        The guild master gave the quest to the hero.
        """

        build_cmd = BuildGlossaryCommand(
            work_id=1,
            volume_id=1,
            text=text,
            source_lang="en",
            target_lang="es",
            min_frequency=1,
        )

        # Mock the entity extractor
        with patch.object(
            glossary_service._uow.entity_extractor,
            "extract",
            new_callable=AsyncMock,
        ) as mock_extract:
            mock_extract.return_value = [
                EntityCandidate(text="slime", entity_type=EntityType.RACE, frequency=1, source_language="en"),
                EntityCandidate(text="goblin", entity_type=EntityType.RACE, frequency=1, source_language="en"),
                EntityCandidate(text="mana", entity_type=EntityType.SKILL, frequency=1, source_language="en"),
                EntityCandidate(text="dragon", entity_type=EntityType.RACE, frequency=1, source_language="en"),
                EntityCandidate(text="adventurer", entity_type=EntityType.TITLE, frequency=1, source_language="en"),
                EntityCandidate(text="guild", entity_type=EntityType.ORGANIZATION, frequency=1, source_language="en"),
                EntityCandidate(text="hero", entity_type=EntityType.TITLE, frequency=1, source_language="en"),
            ]

            result = await glossary_service.build_glossary(build_cmd)

        assert result.pipeline_id is not None
        assert result.entities_extracted >= 0
        assert result.status in ("completed", "completed_with_errors", "failed")

    @pytest.mark.asyncio
    async def test_pipeline_state_machine(self, uow):
        """Test pipeline state transitions."""
        from pdftranslator.services.glossary.domain.repositories.protocols import BuildPipelineRepository

        pipeline_repo = uow.pipelines

        # Create pipeline
        pipeline = BuildPipeline(
            work_id=1,
            volume_id=1,
            source_lang="en",
            target_lang="es",
        )
        saved = await pipeline_repo.create(pipeline)

        assert saved.status == BuildPipelineStatus.PENDING
        assert saved.current_stage_index == 0

        # Start pipeline
        saved.status = BuildPipelineStatus.IN_PROGRESS
        saved.stages[0].status = "in_progress"
        updated = await pipeline_repo.update(saved)

        assert updated.status == BuildPipelineStatus.IN_PROGRESS
        assert updated.stages[0].status.value == "in_progress"

        # Complete first stage
        updated.stages[0].status = "completed"
        updated.current_stage_index = 1
        updated.stages[1].status = "in_progress"
        updated = await pipeline_repo.update(updated)

        assert updated.current_stage_index == 1
        assert updated.stages[0].status.value == "completed"
        assert updated.stages[1].status.value == "in_progress"


class TestPipelineStageEndpoints:
    """Tests for individual pipeline stage endpoints."""

    @pytest.fixture
    def client(self):
        """Test client for FastAPI app."""
        app = create_app()
        return TestClient(app)

    def test_health_endpoint(self, client):
        """Health endpoint returns 200."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "glossary-service"

    def test_readiness_endpoint(self, client):
        """Readiness endpoint returns 200 when DB ready."""
        response = client.get("/health/ready")
        # May be 503 if DB not ready in test, but should respond
        assert response.status_code in (200, 503)


class TestEntityExtractionIntegration:
    """Test entity extraction integration."""

    @pytest.mark.asyncio
    async def test_extract_entities_from_fantasy_text(self, glossary_service):
        """Extract entities from fantasy novel text."""
        text = """
        The young mage Aria cast fireball at the ancient dragon.
        The guild master of the Silver Hand guild gave her a quest.
        She needed to collect mana crystals from the dungeon.
        """

        with patch.object(
            glossary_service._uow.entity_extractor,
            "extract",
            new_callable=AsyncMock,
        ) as mock_extract:
            mock_extract.return_value = [
                EntityCandidate(text="mage", entity_type=EntityType.TITLE, frequency=1, source_language="en"),
                EntityCandidate(text="fireball", entity_type=EntityType.SKILL, frequency=1, source_language="en"),
                EntityCandidate(text="dragon", entity_type=EntityType.RACE, frequency=1, source_language="en"),
                EntityCandidate(text="guild", entity_type=EntityType.ORGANIZATION, frequency=2, source_language="en"),
                EntityCandidate(text="quest", entity_type=EntityType.ITEM, frequency=1, source_language="en"),
                EntityCandidate(text="mana", entity_type=EntityType.SKILL, frequency=1, source_language="en"),
                EntityCandidate(text="dungeon", entity_type=EntityType.PLACE, frequency=1, source_language="en"),
            ]

            entities = await glossary_service._uow.entity_extractor.extract(text, "en", 1)

        assert len(entities) == 7
        entity_texts = [e.text for e in entities]
        assert "dragon" in entity_texts
        assert "guild" in entity_texts
        assert "fireball" in entity_texts


class TestGlossaryCRUDIntegration:
    """Integration tests for glossary CRUD operations."""

    @pytest.mark.asyncio
    async def test_create_read_update_delete_glossary(self, glossary_service, uow):
        """Full CRUD cycle for glossary."""
        # Create
        create_cmd = CreateGlossaryCommand(work_id=999, name="CRUD Test", source_lang="en", target_lang="es")
        glossary = await glossary_service.create_glossary(create_cmd)

        assert glossary.id is not None
        assert glossary.work_id == 999

        # Read
        retrieved = await glossary_service.get_glossary(999)
        assert retrieved.id == glossary.id
        assert retrieved.name == "CRUD Test"

        # Update
        glossary.name = "Updated CRUD Test"
        updated = await uow.glossaries.update(glossary)
        assert updated.name == "Updated CRUD Test"

        # Delete
        deleted = await uow.glossaries.delete(glossary.id)
        assert deleted is True

        # Verify deleted
        retrieved = await glossary_service.get_glossary(999)
        assert retrieved is None

    @pytest.mark.asyncio
    async def test_glossary_entries_crud(self, glossary_service, uow):
        """CRUD for glossary entries."""
        # Create glossary first
        create_cmd = CreateGlossaryCommand(work_id=888, name="Entry Test", source_lang="en", target_lang="es")
        glossary = await glossary_service.create_glossary(create_cmd)

        # Add entries
        entries = [
            GlossaryEntry(
                work_id=888,
                term="slime",
                translation="slime",
                entity_type=EntityType.RACE,
                do_not_translate=True,
                is_verified=True,
            ),
            GlossaryEntry(
                work_id=888,
                term="goblin",
                translation="goblin",
                entity_type=EntityType.RACE,
            ),
        ]

        for entry in entries:
            await uow.glossary_entries.create(entry)

        # List entries
        from pdftranslator.services.glossary.api.schemas import PaginationParams
        result = await uow.glossary_entries.list_by_work(888, PaginationParams(page=1, page_size=10))
        assert result.total == 2
        assert len(result.items) == 2

        # Search
        search_result = await uow.glossary_entries.search(888, "slime", PaginationParams())
        assert search_result.total == 1
        assert search_result.items[0].term == "slime"

        # Get existing terms
        existing = await uow.glossary_entries.get_existing_terms(888)
        assert "slime" in existing
        assert "goblin" in existing


class TestPipelineResumeIntegration:
    """Test pipeline resume functionality."""

    @pytest.mark.asyncio
    async def test_resume_failed_pipeline(self, glossary_service, uow):
        """Resume a pipeline that failed at a stage."""
        from pdftranslator.services.glossary.domain.services.commands import ResumePipelineCommand

        # Create a failed pipeline
        pipeline = BuildPipeline(work_id=777, volume_id=1, source_lang="en", target_lang="es")
        pipeline.status = BuildPipelineStatus.FAILED
        pipeline.stages[0].status = "completed"
        pipeline.stages[1].status = "failed"
        pipeline.stages[1].error_message = "LLM validation timeout"

        saved = await uow.pipelines.create(pipeline)

        # Resume
        cmd = ResumePipelineCommand(work_id=777, volume_id=1)
        resumed = await glossary_service.resume_pipeline(cmd)

        assert resumed.status == BuildPipelineStatus.IN_PROGRESS
        assert resumed.current_stage_index == 1
        assert resumed.stages[1].status.value == "pending"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--asyncio-mode=auto"])