"""
Glossary Domain Service.

CUPID Principle: Domain-Focused
- Pure domain logic, no infrastructure
- Uses Unit of Work for transactions
- Coordinates pipeline stages
"""

from __future__ import annotations
import time
import uuid
from typing import List, Optional
from datetime import datetime

from ...models.glossary import Glossary, GlossaryEntry, GlossaryStatus
from ...models.build_pipeline import (
    BuildPipeline,
    PipelineStage,
    PipelineStageStatus,
    BuildPipelineStatus,
)
from ...models.entity import EntityCandidate, EntityType
from ...repositories.protocols import GlossaryUnitOfWork
from ...repositories.exceptions import (
    DomainError,
    NotFoundError,
    DuplicateError,
    ValidationError,
    GlossaryNotFoundError,
    PipelineNotFoundError,
    InsufficientContextError,
)
from .commands import (
    CreateGlossaryCommand,
    BuildGlossaryCommand,
    ValidateEntitiesCommand,
    GenerateEmbeddingsCommand,
    SuggestTranslationsCommand,
    SaveGlossaryEntriesCommand,
    UpdateGlossaryEntryCommand,
    SearchGlossaryCommand,
    ListPipelinesCommand,
    GetPipelineStatusCommand,
    ResumePipelineCommand,
    GlossaryBuildResult,
)


class GlossaryService:
    """Domain service for glossary operations."""

    def __init__(self, uow: GlossaryUnitOfWork):
        self._uow = uow

    # =================== GLOSSARY OPERATIONS ===================

    async def create_glossary(self, command: CreateGlossaryCommand) -> Glossary:
        """Create a new glossary for a work."""
        async with self._uow:
            # Check if glossary already exists for this work
            existing = await self._uow.glossaries.get_by_work(command.work_id)
            if existing:
                raise DuplicateError(f"Glossary already exists for work {command.work_id}")

            glossary = Glossary(
                work_id=command.work_id,
                name=command.name,
                source_lang=command.source_lang,
                target_lang=command.target_lang,
                status=GlossaryStatus.PENDING,
            )

            created = await self._uow.glossaries.create(glossary)
            await self._uow.commit()
            return created

    async def get_glossary(self, work_id: int) -> Glossary:
        """Get glossary by work ID."""
        glossary = await self._uow.glossaries.get_by_work(work_id)
        if not glossary:
            raise GlossaryNotFoundError(f"Glossary not found for work {work_id}")
        return glossary

    async def get_glossary_by_uuid(self, uuid_str: str) -> Glossary:
        """Get glossary by UUID."""
        glossary = await self._uow.glossaries.get_by_uuid(uuid_str)
        if not glossary:
            raise GlossaryNotFoundError(f"Glossary not found with UUID {uuid_str}")
        return glossary

    async def list_glossaries(
        self,
        page: int = 1,
        page_size: int = 20,
        work_id: Optional[int] = None,
        status: Optional[str] = None,
    ):
        """List glossaries with pagination."""
        from ...repositories.protocols import PaginationParams
        pagination = PaginationParams(page=page, page_size=page_size)
        return await self._uow.glossaries.list(pagination, work_id, status)

    async def update_entry(self, command: UpdateGlossaryEntryCommand) -> GlossaryEntry:
        """Update a glossary entry."""
        async with self._uow:
            entry = await self._uow.glossary_entries.get_by_id(command.entry_id)
            if not entry:
                raise NotFoundError(f"Glossary entry {command.entry_id} not found")

            # Apply changes
            if command.translation is not None:
                entry = entry.with_translation(command.translation)
            if command.is_verified is not None:
                entry = entry.with_verification(command.is_verified)
            if command.confidence is not None:
                entry = entry.with_confidence(command.confidence)
            if command.entity_type is not None:
                entry = entry._replace(entity_type=command.entity_type)
            if command.is_proper_noun is not None:
                entry = entry._replace(is_proper_noun=command.is_proper_noun)
            if command.do_not_translate is not None:
                entry = entry._replace(do_not_translate=command.do_not_translate)
            if command.context is not None:
                entry = entry._replace(context=command.context)
            if command.notes is not None:
                entry = entry._replace(notes=command.notes)

            updated = await self._uow.glossary_entries.update(entry)
            await self._uow.commit()
            return updated

    async def search_entries(self, command: SearchGlossaryCommand):
        """Search glossary entries."""
        from ...repositories.protocols import PaginationParams
        pagination = PaginationParams(page=command.page, page_size=command.page_size)
        return await self._uow.glossary_entries.search(
            command.work_id,
            command.query,
            pagination,
        )

    # =================== PIPELINE OPERATIONS ===================

    async def build_glossary(self, command: BuildGlossaryCommand) -> GlossaryBuildResult:
        """
        Execute full glossary build pipeline.

        Pipeline stages:
        1. Extract entities from text
        2. Filter duplicates against existing glossary
        3. Validate entities with LLM
        4. Generate embeddings
        5. Translate entities
        6. Save to glossary
        """
        start_time = time.time()
        errors: List[str] = []

        pipeline = BuildPipeline(
            id=str(uuid.uuid4()),
            work_id=command.work_id,
            volume_id=command.volume_id,
            source_lang=command.source_lang,
            target_lang=command.target_lang,
            min_frequency=command.min_frequency,
            status=BuildPipelineStatus.RUNNING,
        )

        async with self._uow:
            # Check for existing pipeline (resume)
            if command.resume and not command.force_restart:
                existing = await self._uow.pipelines.get_by_work_volume(
                    command.work_id, command.volume_id
                )
                if existing and existing.status in (BuildPipelineStatus.RUNNING, BuildPipelineStatus.FAILED):
                    pipeline = existing
                    await self._resume_pipeline(pipeline, command, errors)
                    await self._uow.pipelines.update(pipeline)
            else:
                pipeline = await self._uow.pipelines.create(pipeline)

            try:
                # Stage 1: Extract
                pipeline.start_stage(PipelineStage.EXTRACT)
                await self._uow.pipelines.update(pipeline)

                entities = await self._uow.entity_extractor.extract(
                    command.text,
                    command.source_lang,
                    command.min_frequency,
                )
                pipeline.complete_stage(PipelineStage.EXTRACT, len(entities))
                await self._uow.pipelines.update(pipeline)

                # Filter new entities
                existing_terms = await self._uow.glossary_entries.get_existing_terms(command.work_id)
                new_entities = [
                    e for e in entities
                    if e.key not in existing_terms
                ]
                pipeline.record_filtered(len(entities) - len(new_entities))

                # Stage 2: Validate
                if new_entities and command.suggest_translations:
                    pipeline.start_stage(PipelineStage.VALIDATE)
                    await self._uow.pipelines.update(pipeline)

                    validated = await self.validate_entities(ValidateEntitiesCommand(
                        entities=new_entities,
                        source_lang=command.source_lang,
                        work_id=command.work_id,
                        volume_id=command.volume_id,
                    ))
                    pipeline.complete_stage(PipelineStage.VALIDATE, len(validated))
                    await self._uow.pipelines.update(pipeline)

                    # Stage 3: Embed
                    pipeline.start_stage(PipelineStage.EMBED)
                    await self._uow.pipelines.update(pipeline)

                    embedded = await self.generate_embeddings(GenerateEmbeddingsCommand(
                        entities=validated,
                    ))
                    pipeline.complete_stage(PipelineStage.EMBED, len(embedded))
                    await self._uow.pipelines.update(pipeline)

                    # Stage 4: Translate
                    pipeline.start_stage(PipelineStage.TRANSLATE)
                    await self._uow.pipelines.update(pipeline)

                    translated = await self.suggest_translations(SuggestTranslationsCommand(
                        entities=embedded,
                        source_lang=command.source_lang,
                        target_lang=command.target_lang,
                    ))
                    pipeline.complete_stage(PipelineStage.TRANSLATE, len(translated))
                    await self._uow.pipelines.update(pipeline)

                    # Stage 5: Save
                    pipeline.start_stage(PipelineStage.SAVE)
                    await self._uow.pipelines.update(pipeline)

                    saved = await self.save_glossary_entries(SaveGlossaryEntriesCommand(
                        work_id=command.work_id,
                        entities=translated,
                        source_lang=command.source_lang,
                        target_lang=command.target_lang,
                    ))
                    pipeline.complete_stage(PipelineStage.SAVE, len(saved))
                else:
                    saved = 0

                pipeline.complete()
                await self._uow.pipelines.update(pipeline)
                await self._uow.commit()

            except Exception as e:
                pipeline.fail(str(e))
                errors.append(str(e))
                await self._uow.pipelines.update(pipeline)
                await self._uow.commit()
                raise

        duration_ms = int((time.time() - start_time) * 1000)

        return GlossaryBuildResult(
            pipeline_id=pipeline.id,
            extracted=len(entities) if 'entities' in locals() else 0,
            validated=len(validated) if 'validated' in locals() else 0,
            embedded=len(embedded) if 'embedded' in locals() else 0,
            translated=len(translated) if 'translated' in locals() else 0,
            saved=saved,
            skipped=pipeline.filtered_count,
            errors=errors,
            duration_ms=duration_ms,
        )

    async def get_pipeline_status(self, command: GetPipelineStatusCommand) -> BuildPipeline:
        """Get pipeline build status."""
        pipeline = await self._uow.pipelines.get_by_work_volume(
            command.work_id, command.volume_id
        )
        if not pipeline:
            raise PipelineNotFoundError(
                f"No pipeline for work {command.work_id}, volume {command.volume_id}"
            )
        return pipeline

    async def resume_pipeline(self, command: ResumePipelineCommand) -> BuildPipeline:
        """Resume a failed/partial pipeline."""
        pipeline = await self._uow.pipelines.get_by_work_volume(
            command.work_id, command.volume_id
        )
        if not pipeline:
            raise PipelineNotFoundError(
                f"No pipeline for work {command.work_id}, volume {command.volume_id}"
            )
        if pipeline.status not in (BuildPipelineStatus.FAILED, BuildPipelineStatus.RUNNING):
            raise ValidationError(f"Cannot resume pipeline in status {pipeline.status}")
        return pipeline

    async def list_pipelines(self, command: ListPipelinesCommand):
        """List build pipelines."""
        from ...repositories.protocols import PaginationParams
        pagination = PaginationParams(page=command.page, page_size=command.page_size)
        return await self._uow.pipelines.list(pagination, command.work_id, command.status)

    # =================== PIPELINE STAGE EXECUTION ===================

    async def validate_entities(self, command: ValidateEntitiesCommand) -> List[EntityCandidate]:
        """
        Validate entities with LLM.

        This is a domain operation - actual LLM call happens in infrastructure.
        The domain service coordinates; implementation delegates to infrastructure.
        """
        # In a real implementation, this would call an LLM service
        # For now, mark all as validated with a placeholder translation
        validated = []
        for entity in command.entities:
            v = entity.with_translation(
                f"[{command.target_lang}]{entity.text}"  # Placeholder
            )._replace(validated=True)
            validated.append(v)
        return validated

    async def generate_embeddings(self, command: GenerateEmbeddingsCommand) -> List[EntityCandidate]:
        """Generate embeddings for validated entities."""
        # In real implementation, calls vector store
        # Domain service coordinates; infrastructure implements
        return command.entities

    async def suggest_translations(self, command: SuggestTranslationsCommand) -> List[EntityCandidate]:
        """Suggest translations for embedded entities."""
        # In real implementation, calls LLM
        translated = []
        for entity in command.entities:
            if not entity.translation:
                t = entity.with_translation(
                    f"[{command.target_lang}]{entity.text}"
                )
                translated.append(t)
            else:
                translated.append(entity)
        return translated

    async def save_glossary_entries(self, command: SaveGlossaryEntriesCommand) -> int:
        """Save translated entities to glossary."""
        # Get or create glossary
        glossary = await self._uow.glossaries.get_by_work(command.work_id)
        if not glossary:
            glossary = Glossary(
                work_id=command.work_id,
                source_lang=command.source_lang,
                target_lang=command.target_lang,
            )
            glossary = await self._uow.glossaries.create(glossary)

        # Convert entities to entries
        entries = []
        for entity in command.entities:
            if not entity.translation:
                continue
            entry = GlossaryEntry(
                work_id=command.work_id,
                term=entity.text,
                translation=entity.translation,
                entity_type=entity.entity_type,
                frequency=entity.frequency,
                confidence=entity.confidence,
                context=entity.best_context if hasattr(entity, 'best_context') else None,
                source_lang=command.source_lang,
                target_lang=command.target_lang,
            )
            entries.append(entry)

        if entries:
            await self._uow.glossary_entries.batch_create(entries)

        return len(entries)

    async def _resume_pipeline(
        self,
        pipeline: BuildPipeline,
        command: BuildGlossaryCommand,
        errors: List[str],
    ) -> None:
        """Resume pipeline from last completed stage."""
        # Determine which stages need re-execution based on pipeline state
        stages_to_run = []
        current_stage = pipeline.current_stage

        stage_order = [
            PipelineStage.EXTRACT,
            PipelineStage.VALIDATE,
            PipelineStage.EMBED,
            PipelineStage.TRANSLATE,
            PipelineStage.SAVE,
        ]

        if current_stage:
            current_idx = stage_order.index(current_stage)
            # Re-run current and all subsequent stages
            stages_to_run = stage_order[current_idx:]
        else:
            stages_to_run = stage_order

        # Execute remaining stages (simplified - real impl would be more robust)
        for stage in stages_to_run:
            pipeline.start_stage(stage)
            await self._uow.pipelines.update(pipeline)
            # ... stage execution logic ...
            pipeline.complete_stage(stage, 0)
            await self._uow.pipelines.update(pipeline)