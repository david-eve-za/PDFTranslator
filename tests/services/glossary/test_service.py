"""
Unit Tests for Glossary Service Domain Services.
"""

import pytest
from unittest.mock import AsyncMock, Mock, AsyncMock, patch
from uuid import UUID

from pdftranslator.services.glossary.domain.services.glossary_service import GlossaryService
from pdftranslator.services.glossary.domain.services.commands import (
    CreateGlossaryCommand,
    BuildGlossaryCommand,
    UpdateGlossaryEntryCommand,
    SearchGlossaryCommand,
)
from pdftranslator.services.glossary.domain.models.glossary import Glossary, GlossaryEntry, GlossaryStatus
from pdftranslator.services.glossary.domain.models.entity import EntityCandidate, EntityType
from pdftranslator.services.glossary.domain.models.build_pipeline import BuildPipeline, BuildPipelineStatus


class TestGlossaryService:
    """Tests for GlossaryService."""

    @pytest.fixture
    def mock_uow(self):
        """Mock Unit of Work."""
        uow = Mock()
        uow.glossaries = Mock()
        uow.glossary_entries = Mock()
        uow.pipelines = Mock()
        uow.entity_extractor = Mock()
        uow.__aenter__ = AsyncMock(return_value=uow)
        uow.__aexit__ = AsyncMock(return_value=None)
        uow.commit = AsyncMock()
        uow.rollback = AsyncMock()
        return uow

    @pytest.fixture
    def service(self, mock_uow):
        """Glossary service with mocked dependencies."""
        return GlossaryService(mock_uow)

    @pytest.mark.asyncio
    async def test_create_glossary(self, service, mock_uow):
        """Test creating a glossary."""
        # Setup
        mock_glossary = Glossary(
            id=1,
            uuid=UUID("12345678-1234-5678-1234-567812345678"),
            work_id=1,
            name="Test Glossary",
            source_lang="en",
            target_lang="es",
        )
        mock_uow.glossaries.create = AsyncMock(return_value=mock_glossary)

        # Execute
        command = CreateGlossaryCommand(
            work_id=1,
            name="Test Glossary",
            source_lang="en",
            target_lang="es",
        )
        result = await service.create_glossary(command)

        # Assert
        assert result.work_id == 1
        assert result.name == "Test Glossary"
        mock_uow.glossaries.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_build_glossary_creates_pipeline(self, service, mock_uow):
        """Test building glossary creates pipeline."""
        # Setup
        mock_pipeline = BuildPipeline(
            work_id=1,
            volume_id=1,
            source_lang="en",
            target_lang="es",
        )
        mock_pipeline.status = BuildPipelineStatus.COMPLETED
        mock_pipeline.entities_extracted = 5
        mock_pipeline.entities_filtered = 3
        mock_pipeline.entities_validated = 3
        mock_pipeline.entities_embedded = 3
        mock_pipeline.entities_translated = 3
        mock_pipeline.entities_saved = 3
        mock_pipeline.duration_seconds = 1.5

        mock_uow.pipelines.create = AsyncMock(return_value=mock_pipeline)
        mock_uow.pipelines.update = AsyncMock(return_value=mock_pipeline)
        mock_uow.entity_extractor.extract = AsyncMock(return_value=[])
        mock_uow.glossary_entries.get_existing_terms = AsyncMock(return_value=set())

        # Execute
        command = BuildGlossaryCommand(
            work_id=1,
            volume_id=1,
            text="Test text",
            source_lang="en",
            target_lang="es",
            min_frequency=1,
        )
        result = await service.build_glossary(command)

        # Assert
        assert result.pipeline_id == mock_pipeline.id
        assert result.status == "completed"
        mock_uow.pipelines.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_entry(self, service, mock_uow):
        """Test updating a glossary entry."""
        # Setup
        mock_entry = GlossaryEntry(
            id=1,
            uuid=UUID("12345678-1234-5678-1234-567812345678"),
            work_id=1,
            term="test",
            translation="prueba",
            is_verified=True,
            confidence=0.9,
        )
        mock_uow.glossary_entries.update = AsyncMock(return_value=mock_entry)

        # Execute
        command = UpdateGlossaryEntryCommand(
            entry_id=1,
            translation="updated",
            is_verified=True,
            confidence=0.95,
        )
        result = await service.update_entry(command)

        # Assert
        assert result.translation == "updated"
        assert result.is_verified is True
        assert result.confidence == 0.95

    @pytest.mark.asyncio
    async def test_search_entries(self, service, mock_uow):
        """Test searching glossary entries."""
        # Setup
        mock_results = [
            GlossaryEntry(id=1, work_id=1, term="test", translation="prueba", is_verified=True),
            GlossaryEntry(id=2, work_id=1, term="test2", translation="prueba2", is_verified=False),
        ]
        mock_paginated = Mock()
        mock_paginated.items = mock_results
        mock_paginated.total = 2
        mock_paginated.page = 1
        mock_paginated.page_size = 20
        mock_uow.glossary_entries.search = AsyncMock(return_value=mock_paginated)

        # Execute
        command = SearchGlossaryCommand(
            work_id=1,
            query="test",
            page=1,
            page_size=20,
        )
        result = await service.search_entries(command)

        # Assert
        assert result.total == 2
        assert len(result.items) == 2


class TestGlossaryServiceValidation:
    """Tests for service validation."""

    @pytest.fixture
    def mock_uow(self):
        uow = Mock()
        uow.glossaries = Mock()
        uow.glossary_entries = Mock()
        uow.pipelines = Mock()
        uow.entity_extractor = Mock()
        uow.__aenter__ = AsyncMock(return_value=uow)
        uow.__aexit__ = AsyncMock(return_value=None)
        return uow

    @pytest.fixture
    def service(self, mock_uow):
        return GlossaryService(mock_uow)

    @pytest.mark.asyncio
    async def test_build_glossary_requires_text(self, service):
        """Build glossary fails with empty text."""
        command = BuildGlossaryCommand(
            work_id=1,
            volume_id=1,
            text="",
            source_lang="en",
            target_lang="es",
        )
        with pytest.raises(ValueError, match="text"):
            await service.build_glossary(command)

    @pytest.mark.asyncio
    async def test_build_glossary_requires_valid_lang(self, service):
        """Build glossary fails with invalid language."""
        command = BuildGlossaryCommand(
            work_id=1,
            volume_id=1,
            text="test",
            source_lang="invalid",
            target_lang="es",
        )
        with pytest.raises(ValueError):
            await service.build_glossary(command)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])