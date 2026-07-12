"""
Unit Tests for Glossary Domain Models.

CUPID Principle: Composable
- Test domain models in isolation
- No infrastructure dependencies
"""

from __future__ import annotations
import pytest
from uuid import UUID, uuid4
from datetime import datetime

from pdftranslator.services.glossary.domain.models.glossary import (
    Glossary,
    GlossaryEntry,
    GlossaryStatus,
)
from pdftranslator.services.glossary.domain.models.entity import (
    EntityCandidate,
    EntityType,
)
from pdftranslator.services.glossary.domain.models.build_pipeline import (
    BuildPipeline,
    StageExecution,
    PipelineStageEnum,
    BuildPipelineStatus,
    PipelineStageStatus,
)


class TestGlossaryModel:
    """Tests for Glossary aggregate."""

    def test_create_glossary(self):
        """Create glossary with required fields."""
        glossary = Glossary(
            work_id=1,
            name="Test Glossary",
            source_lang="en",
            target_lang="es",
        )
        assert glossary.work_id == 1
        assert glossary.name == "Test Glossary"
        assert glossary.status == GlossaryStatus.DRAFT
        assert isinstance(glossary.uuid, UUID)

    def test_glossary_entry_count(self):
        """Entry count property works."""
        glossary = Glossary(work_id=1, name="Test", source_lang="en", target_lang="es")
        assert glossary.entry_count == 0

        # Add entries
        entry = GlossaryEntry(
            work_id=1,
            term="test",
            translation="prueba",
            entity_type=EntityType.OTHER,
        )
        glossary.add_entry(entry)
        assert glossary.entry_count == 1

    def test_glossary_verification_progress(self):
        """Verified count and completion percent work."""
        glossary = Glossary(work_id=1, name="Test", source_lang="en", target_lang="es")

        entry1 = GlossaryEntry(work_id=1, term="verified", translation="verificado", is_verified=True)
        entry2 = GlossaryEntry(work_id=1, term="unverified", translation="no verificado", is_verified=False)

        glossary.add_entry(entry1)
        glossary.add_entry(entry2)

        assert glossary.entry_count == 2
        assert glossary.verified_count == 1
        assert glossary.completion_percent == 50.0


class TestGlossaryEntryModel:
    """Tests for GlossaryEntry entity."""

    def test_create_entry(self):
        """Create entry with required fields."""
        entry = GlossaryEntry(
            work_id=1,
            term="slime",
            translation="gelatina",
            entity_type=EntityType.RACE,
            is_proper_noun=True,
        )
        assert entry.term == "slime"
        assert entry.entity_type == EntityType.RACE
        assert entry.is_proper_noun is True

    def test_effective_translation(self):
        """Effective translation returns translation or term if DNT."""
        entry_dnt = GlossaryEntry(
            work_id=1,
            term="slime",
            translation="baba",
            do_not_translate=True,
        )
        assert entry_dnt.effective_translation == "slime"

        entry_normal = GlossaryEntry(
            work_id=1,
            term="goblin",
            translation="goblin",
            do_not_translate=False,
        )
        assert entry_normal.effective_translation == "goblin"

    def test_key_property(self):
        """Key normalizes term for comparison."""
        entry = GlossaryEntry(work_id=1, term="  SLIME  ", translation="slime")
        assert entry.key == "slime"

    def test_entry_comparison(self):
        """Entries compare by key."""
        entry1 = GlossaryEntry(work_id=1, term="slime", translation="slime")
        entry2 = GlossaryEntry(work_id=2, term="SLIME", translation="gelatina")
        assert entry1 == entry2


class TestEntityCandidateModel:
    """Tests for EntityCandidate value object."""

    def test_create_entity(self):
        """Create entity candidate with required fields."""
        entity = EntityCandidate(
            text="slime",
            entity_type=EntityType.RACE,
            frequency=3,
            source_language="en",
        )
        assert entity.text == "slime"
        assert entity.entity_type == EntityType.RACE
        assert entity.frequency == 3
        assert entity.validated is False

    def test_entity_equality(self):
        """Entities equal by text (case-insensitive)."""
        e1 = EntityCandidate(text="slime", entity_type=EntityType.RACE, frequency=1, source_language="en")
        e2 = EntityCandidate(text="SLIME", entity_type=EntityType.RACE, frequency=1, source_language="en")
        assert e1 == e2

    def test_entity_hash(self):
        """Entities can be used in sets."""
        e1 = EntityCandidate(text="slime", entity_type=EntityType.RACE, frequency=1, source_language="en")
        e2 = EntityCandidate(text="goblin", entity_type=EntityType.RACE, frequency=1, source_language="en")
        entity_set = {e1, e2}
        assert len(entity_set) == 2


class TestEntityType:
    """Tests for EntityType enum."""

    def test_from_str(self):
        """Parse strings to entity types."""
        assert EntityType.from_str("character") == EntityType.CHARACTER
        assert EntityType.from_str("PLACE") == EntityType.PLACE
        assert EntityType.from_str("unknown") == EntityType.OTHER

    def test_fantasy_types(self):
        """Fantasy-specific types available."""
        assert EntityType.RACE == EntityType.RACE
        assert EntityType.SKILL == EntityType.SKILL
        assert EntityType.ORGANIZATION == EntityType.ORGANIZATION


class TestBuildPipeline:
    """Tests for BuildPipeline aggregate."""

    def test_create_pipeline(self):
        """Create pipeline with required fields."""
        pipeline = BuildPipeline(
            work_id=1,
            volume_id=1,
            source_lang="en",
            target_lang="es",
        )
        assert pipeline.work_id == 1
        assert pipeline.volume_id == 1
        assert pipeline.status == BuildPipelineStatus.PENDING
        assert isinstance(pipeline.id, UUID)

    def test_pipeline_stages_initialized(self):
        """Pipeline initializes all stages."""
        pipeline = BuildPipeline(work_id=1, volume_id=1, source_lang="en", target_lang="es")
        assert len(pipeline.stages) == len(PipelineStageEnum.all())

        stage_names = [s.name for s in pipeline.stages]
        expected = PipelineStageEnum.all()
        assert stage_names == expected

    def test_progress_calculation(self):
        """Progress percent calculated correctly."""
        pipeline = BuildPipeline(work_id=1, volume_id=1, source_lang="en", target_lang="es")
        assert pipeline.progress_percent == 0.0

        # Mark first stage as completed
        pipeline.stages[0].status = PipelineStageStatus.COMPLETED
        assert abs(pipeline.progress_percent - 16.67) < 0.1  # 1/6 stages

    def test_current_stage(self):
        """Get current executing stage."""
        pipeline = BuildPipeline(work_id=1, volume_id=1, source_lang="en", target_lang="es")
        assert pipeline.current_stage.name == PipelineStageEnum.EXTRACT

        # Complete first stage
        pipeline.stages[0].status = PipelineStageStatus.COMPLETED
        pipeline.stages[1].status = PipelineStageStatus.IN_PROGRESS
        assert pipeline.current_stage.name == PipelineStageEnum.FILTER


class TestStageExecution:
    """Tests for StageExecution entity."""

    def test_stage_duration(self):
        """Duration calculated from start/complete times."""
        stage = StageExecution(
            name=PipelineStageEnum.EXTRACT,
            status=PipelineStageStatus.COMPLETED,
        )
        stage.started_at = datetime(2024, 1, 1, 12, 0, 0)
        stage.completed_at = datetime(2024, 1, 1, 12, 0, 5)
        assert stage.duration_seconds == 5.0

    def test_stage_retry_increment(self):
        """Retry count increments."""
        stage = StageExecution(name=PipelineStageEnum.EXTRACT)
        assert stage.retry_count == 0

        stage.retry_count += 1
        assert stage.retry_count == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])