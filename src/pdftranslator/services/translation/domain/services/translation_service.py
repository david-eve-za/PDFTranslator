"""
Translation Domain Service - Business Logic.

CUPID Principle: Domain-Focused
- Pure domain logic, no infrastructure
- Uses Unit of Work for transactions
- Coordinates pipeline stages
"""

from __future__ import annotations
import time
import uuid
import re
from typing import Optional, List
from datetime import datetime

from ..models.job import TranslationJob, JobStatus, JobPriority
from ..models.segment import Segment
from ..models.glossary_ref import GlossaryReference
from ..repositories.protocols import (
    TranslationJobRepository,
    SegmentRepository,
    TranslationUnitOfWork,
    PaginationParams,
    PaginatedResult,
    TranslationPipelineRepository,
    TranslationPipelineStageRepository,
    TranslationPipeline,
    PipelineStage,
)
from ..repositories.exceptions import DomainError, NotFoundError
from .commands import (
    CreateJobCommand,
    CreateSegmentsCommand,
    DetectLanguageCommand,
    SegmentTextCommand,
    TranslateSegmentsCommand,
    QualityCheckCommand,
    StoreTranslationsCommand,
    CreatePipelineCommand,
    GetPipelineStatusCommand,
    ResumePipelineCommand,
    DetectLanguageResult,
    SegmentTextResult,
    TranslateSegmentsResult,
    QualityCheckResult,
    StoreTranslationsResult,
    TranslationPipelineResult,
)


class TranslationService:
    """Domain service for translation operations."""

    def __init__(self, uow: TranslationUnitOfWork):
        self._uow = uow

    # =================== JOB OPERATIONS ===================

    async def create_job(self, command: CreateJobCommand) -> TranslationJob:
        job = TranslationJob(
            source_lang=command.source_lang,
            target_lang=command.target_lang,
            work_id=command.work_id,
            volume_id=command.volume_id,
            source_text=command.source_text,
            priority=command.priority,
            llm_provider=command.llm_provider,
            model_name=command.model_name,
        )

        async with self._uow:
            created = await self._uow.jobs.create(job)
            await self._uow.commit()
            return created

    async def get_job(self, job_id: int) -> TranslationJob:
        job = await self._uow.jobs.get_by_id(job_id)
        if not job:
            raise NotFoundError(f"Translation job {job_id} not found")

        # Load segments
        segments = await self._uow.segments.get_by_job_id(job_id)
        job._segments = segments
        return job

    async def get_job_by_uuid(self, uuid_str: str) -> TranslationJob:
        job = await self._uow.jobs.get_by_uuid(uuid_str)
        if not job:
            raise NotFoundError(f"Translation job with UUID {uuid_str} not found")
        return job

    async def list_jobs(
        self,
        pagination: PaginationParams,
        status: Optional[JobStatus] = None,
        work_id: Optional[int] = None,
    ) -> PaginatedResult[TranslationJob]:
        return await self._uow.jobs.get_all(pagination, status, work_id)

    async def update_job_status(
        self,
        job_id: int,
        status: JobStatus,
        error_message: Optional[str] = None,
        target_text: Optional[str] = None,
    ) -> TranslationJob:
        async with self._uow:
            job = await self._uow.jobs.get_by_id(job_id)
            if not job:
                raise NotFoundError(f"Translation job {job_id} not found")

            if status == JobStatus.QUEUED:
                job.queue()
            elif status == JobStatus.IN_PROGRESS:
                if not job.llm_provider or not job.model_name:
                    raise DomainError("LLM provider and model required to start")
                job.start(job.llm_provider, job.model_name)
            elif status == JobStatus.COMPLETED:
                job.complete(target_text or "")
            elif status == JobStatus.FAILED:
                job.fail(error_message or "Unknown error")
            elif status == JobStatus.PAUSED:
                job.pause()
            elif status == JobStatus.CANCELLED:
                job.cancel()
            else:
                raise DomainError(f"Invalid status: {status}")

            updated = await self._uow.jobs.update(job)
            await self._uow.commit()
            return updated

    async def delete_job(self, job_id: int) -> bool:
        async with self._uow:
            job = await self._uow.jobs.get_by_id(job_id)
            if not job:
                raise NotFoundError(f"Translation job {job_id} not found")
            deleted = await self._uow.jobs.delete(job_id)
            await self._uow.commit()
            return deleted

    # =================== SEGMENT OPERATIONS ===================

    async def create_segments(self, command: CreateSegmentsCommand) -> List[Segment]:
        async with self._uow:
            job = await self._uow.jobs.get_by_id(command.job_id)
            if not job:
                raise NotFoundError(f"Translation job {command.job_id} not found")

            created_segments = []
            for segment in command.segments:
                job.add_segment(segment)
                created = await self._uow.segments.create(segment)
                created_segments.append(created)

            await self._uow.commit()
            return created_segments

    async def get_segments_for_job(self, job_id: int) -> List[Segment]:
        job = await self._uow.jobs.get_by_id(job_id)
        if not job:
            raise NotFoundError(f"Translation job {job_id} not found")
        return await self._uow.segments.get_by_job_id(job_id)

    async def get_segment(self, segment_id: int) -> Segment:
        segment = await self._uow.segments.get_by_id(segment_id)
        if not segment:
            raise NotFoundError(f"Segment {segment_id} not found")
        return segment

    async def update_segment_translation(self, segment_id: int, target_text: str) -> Segment:
        async with self._uow:
            segment = await self._uow.segments.get_by_id(segment_id)
            if not segment:
                raise NotFoundError(f"Segment {segment_id} not found")
            segment.set_target_text(target_text)
            updated = await self._uow.segments.update(segment)
            await self._uow.commit()
            return updated

    # =================== PIPELINE STAGE OPERATIONS ===================

    # Stage 1: Detect Language
    async def detect_language(self, command: DetectLanguageCommand) -> DetectLanguageResult:
        """
        Stage 1: Detect source language and analyze text properties.

        This is a domain operation - actual detection delegates to infrastructure.
        """
        text = command.text.strip()
        char_count = len(text)
        word_count = len(text.split())
        line_count = text.count('\n') + 1

        # Simple heuristic detection (in production, use langdetect or similar)
        detected_lang = self._detect_language_heuristic(text)
        confidence = 0.85  # Placeholder

        return DetectLanguageResult(
            detected_lang=detected_lang,
            confidence=confidence,
            text_stats={
                "char_count": char_count,
                "word_count": word_count,
                "line_count": line_count,
                "avg_word_length": char_count / word_count if word_count > 0 else 0,
            },
        )

    def _detect_language_heuristic(self, text: str) -> str:
        """Simple language detection heuristic."""
        # Check for common Spanish words
        spanish_words = {'el', 'la', 'de', 'que', 'y', 'en', 'un', 'es', 'se', 'no', 'te', 'lo', 'le', 'da', 'su', 'por', 'son', 'con', 'para', 'al', 'del', 'los', 'las', 'una', 'como', 'más', 'pero', 'sus', 'le', 'ya', 'o', 'este', 'sí', 'porque', 'esta', 'entre', 'cuando', 'muy', 'sin', 'sobre', 'también', 'me', 'hasta', 'hay', 'donde', 'han', 'quien', 'están', 'estado', 'desde', 'todo', 'nos', 'durante', 'todos', 'uno', 'les', 'ni', 'contra', 'otros', 'ese', 'eso', 'ante', 'ellos', 'e', 'esto', 'mí', 'antes', 'algunos', 'qué', 'unos', 'yo', 'otro', 'otras', 'otra', 'él', 'tanto', 'esa', 'estos', 'mucho', 'quienes', 'nada', 'muchos', 'cual', 'poco', 'ella', 'estar', 'estas', 'algunas', 'algo', 'nosotros', 'mis', 'tú', 'te', 'ti', 'tu', 'tus', 'ellas', 'nosotras', 'vosotros', 'vosotras', 'os', 'mío', 'mía', 'míos', 'mías', 'tuyo', 'tuya', 'tuyos', 'tuyas', 'suyo', 'suya', 'suyos', 'suyas', 'nuestro', 'nuestra', 'nuestros', 'nuestras', 'vuestro', 'vuestra', 'vuestros', 'vuestras', 'mío', 'mía'}
        words = text.lower().split()
        spanish_count = sum(1 for w in words if w in spanish_words)
        if spanish_count > len(words) * 0.15:
            return "es"

        # Check for common English words
        english_words = {'the', 'be', 'to', 'of', 'and', 'a', 'in', 'that', 'have', 'i', 'it', 'for', 'not', 'on', 'with', 'he', 'as', 'you', 'do', 'at', 'this', 'but', 'his', 'by', 'from', 'they', 'we', 'say', 'her', 'she', 'or', 'an', 'will', 'my', 'one', 'all', 'would', 'there', 'their', 'what', 'so', 'up', 'out', 'if', 'about', 'who', 'get', 'which', 'go', 'me'}
        english_count = sum(1 for w in words if w in english_words)
        if english_count > len(words) * 0.15:
            return "en"

        # Default to English
        return "en"

    # Stage 2: Segment Text
    async def segment_text(self, command: SegmentTextCommand) -> SegmentTextResult:
        """
        Stage 2: Segment text into translation units.

        Splits text by sentences, respecting max segment length.
        """
        text = command.text.strip()
        segments = []

        # Split by sentences
        if command.split_by_sentences:
            # Simple sentence splitting (production would use NLTK/spaCy)
            sentences = self._split_sentences(text)
        else:
            sentences = [text]

        segment_number = 1
        current_segment = ""

        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue

            # Check if adding this sentence exceeds max length
            if current_segment and len(current_segment) + len(sentence) + 1 > command.max_segment_length:
                # Save current segment
                if current_segment.strip():
                    segments.append(Segment(
                        job_id=command.job_id,
                        segment_number=segment_number,
                        source_text=current_segment.strip(),
                        target_text=None,
                        created_at=datetime.utcnow(),
                        updated_at=datetime.utcnow(),
                    ))
                    segment_number += 1
                current_segment = sentence
            else:
                if current_segment:
                    current_segment += " " + sentence
                else:
                    current_segment = sentence

        # Don't forget the last segment
        if current_segment.strip():
            segments.append(Segment(
                job_id=command.job_id,
                segment_number=segment_number,
                source_text=current_segment.strip(),
                target_text=None,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            ))

        total_chars = sum(len(s.source_text or "") for s in segments)

        return SegmentTextResult(
            segments=segments,
            total_segments=len(segments),
            total_chars=total_chars,
        )

    def _split_sentences(self, text: str) -> List[str]:
        """Simple sentence splitting. Production should use NLTK/spaCy."""
        # Split on common sentence endings
        # Handle abbreviations, numbers, etc.
        pattern = r'(?<=[.!?])\s+(?=[A-ZÁÉÍÓÚÑ])'
        sentences = re.split(pattern, text)
        return [s.strip() for s in sentences if s.strip()]

    # Stage 3: Translate Segments
    async def translate_segments(self, command: TranslateSegmentsCommand) -> TranslateSegmentsResult:
        """
        Stage 3: Translate segments using LLM.

        Domain service coordinates; actual LLM call happens in infrastructure.
        """
        start_time = time.time()

        async with self._uow:
            job = await self._uow.jobs.get_by_id(command.job_id)
            if not job:
                raise NotFoundError(f"Translation job {command.job_id} not found")

            # Get segments to translate
            if command.segment_ids:
                segments = []
                for seg_id in command.segment_ids:
                    seg = await self._uow.segments.get_by_id(seg_id)
                    if seg and seg.job_id == command.job_id:
                        segments.append(seg)
            else:
                # Get all untranslated segments
                all_segments = await self._uow.segments.get_by_job_id(command.job_id)
                segments = [s for s in all_segments if not s.is_translated]

            translated_count = 0
            failed_count = 0
            errors = []

            for segment in segments:
                try:
                    # In real implementation, call LLM service
                    # For now, simulate with placeholder
                    translated_text = await self._translate_segment(
                        segment.source_text,
                        job.source_lang,
                        job.target_lang,
                        command.llm_provider,
                        command.model_name,
                        command.temperature,
                        command.max_tokens,
                    )

                    segment.set_target_text(translated_text)
                    await self._uow.segments.update(segment)
                    translated_count += 1

                except Exception as e:
                    failed_count += 1
                    errors.append(f"Segment {segment.segment_number}: {str(e)}")

            # Update job with combined target text
            all_segments = await self._uow.segments.get_by_job_id(command.job_id)
            job.target_text = "\n\n".join(s.target_text for s in all_segments if s.is_translated)
            await self._uow.jobs.update(job)

            await self._uow.commit()

        duration_ms = int((time.time() - start_time) * 1000)

        return TranslateSegmentsResult(
            translated_count=translated_count,
            failed_count=failed_count,
            errors=errors,
            duration_ms=duration_ms,
        )

    async def _translate_segment(
        self,
        source_text: str,
        source_lang: str,
        target_lang: str,
        llm_provider: str,
        model_name: str,
        temperature: float,
        max_tokens: int,
    ) -> str:
        """
        Translate a single segment using LLM.

        In production, this calls the LLM infrastructure.
        For now, returns placeholder translation.
        """
        # Placeholder - real implementation would call LLM infrastructure
        # Example: await self._llm_client.translate(...)
        return f"[{target_lang}] {source_text}"

    # Stage 4: Quality Check
    async def quality_check(self, command: QualityCheckCommand) -> QualityCheckResult:
        """
        Stage 4: Quality check translations.

        Runs configurable checks on translated segments.
        """
        async with self._uow:
            job = await self._uow.jobs.get_by_id(command.job_id)
            if not job:
                raise NotFoundError(f"Translation job {command.job_id} not found")

            # Get segments to check
            if command.segment_ids:
                segments = []
                for seg_id in command.segment_ids:
                    seg = await self._uow.segments.get_by_id(seg_id)
                    if seg and seg.job_id == command.job_id:
                        segments.append(seg)
            else:
                # Check all translated segments
                all_segments = await self._uow.segments.get_by_job_id(command.job_id)
                segments = [s for s in all_segments if s.is_translated]

            checked_count = 0
            passed_count = 0
            failed_count = 0
            issues = []

            for segment in segments:
                checked_count += 1
                segment_passed = True

                for check_type in command.check_types:
                    passed, message = await self._run_quality_check(
                        segment, check_type, job.source_lang, job.target_lang, command.threshold
                    )
                    if not passed:
                        segment_passed = False
                        issues.append({
                            "segment_id": segment.id,
                            "segment_number": segment.segment_number,
                            "check_type": check_type,
                            "severity": "error",
                            "message": message,
                        })

                if segment_passed:
                    passed_count += 1
                else:
                    failed_count += 1

            overall_score = passed_count / checked_count if checked_count > 0 else 1.0

            return QualityCheckResult(
                checked_count=checked_count,
                passed_count=passed_count,
                failed_count=failed_count,
                issues=issues,
                overall_score=overall_score,
            )

    async def _run_quality_check(
        self,
        segment: Segment,
        check_type: str,
        source_lang: str,
        target_lang: str,
        threshold: float,
    ) -> tuple[bool, str]:
        """Run a single quality check on a segment."""
        source = segment.source_text or ""
        target = segment.target_text or ""

        if check_type == "completeness":
            if not target or not target.strip():
                return False, "Translation is empty"
            # Check length ratio
            ratio = len(target) / len(source) if source else 0
            if ratio < 0.1 or ratio > 10:
                return False, f"Length ratio {ratio:.2f} outside expected range"
            return True, ""

        elif check_type == "terminology":
            # Check for untranslated glossary terms (placeholder)
            return True, ""

        elif check_type == "fluency":
            # Basic fluency: check for repeated words, empty translations
            words = target.split()
            if len(words) < 2:
                return False, "Translation too short"
            # Check for excessive repetition
            if len(set(words)) / len(words) < 0.3:
                return False, "Excessive word repetition detected"
            return True, ""

        elif check_type == "consistency":
            # Check consistent terminology within job (placeholder)
            return True, ""

        elif check_type == "formatting":
            # Check if formatting preserved (placeholder)
            return True, ""

        return True, ""

    # Stage 5: Store Translations
    async def store_translations(self, command: StoreTranslationsCommand) -> StoreTranslationsResult:
        """
        Stage 5: Store translated segments and update job status.

        Marks job as completed with final target text.
        """
        async with self._uow:
            job = await self._uow.jobs.get_by_id(command.job_id)
            if not job:
                raise NotFoundError(f"Translation job {command.job_id} not found")

            # Get segments to store
            if command.segment_ids:
                segments = []
                for seg_id in command.segment_ids:
                    seg = await self._uow.segments.get_by_id(seg_id)
                    if seg and seg.job_id == command.job_id:
                        segments.append(seg)
            else:
                segments = await self._uow.segments.get_by_job_id(command.job_id)

            stored_count = 0
            errors = []

            for segment in segments:
                if segment.is_translated:
                    try:
                        # Segment already has target_text, just ensure it's saved
                        await self._uow.segments.update(segment)
                        stored_count += 1
                    except Exception as e:
                        errors.append(f"Segment {segment.segment_number}: {str(e)}")
                else:
                    errors.append(f"Segment {segment.segment_number} not translated")

            # Update job status to completed if all segments translated
            all_segments = await self._uow.segments.get_by_job_id(command.job_id)
            all_translated = all(s.is_translated for s in all_segments)

            if all_translated:
                job.complete("\n\n".join(s.target_text for s in all_segments if s.is_translated))
                await self._uow.jobs.update(job)

            await self._uow.commit()

            return StoreTranslationsResult(
                stored_count=stored_count,
                errors=errors,
            )

    # =================== FULL PIPELINE EXECUTION ===================

    async def run_pipeline(self, command: CreatePipelineCommand) -> TranslationPipelineResult:
        """
        Execute full 5-stage translation pipeline.

        Stages:
        1. Detect language
        2. Segment text
        3. Translate segments
        4. Quality check
        5. Store translations
        """
        start_time = time.time()
        pipeline_id = str(uuid.uuid4())
        errors = []
        stages_completed = []
        stages_skipped = []

        async with self._uow:
            # Create pipeline record
            pipeline = TranslationPipeline(
                id=pipeline_id,
                job_id=command.job_id,
                work_id=command.work_id,
                volume_id=command.volume_id or 0,
                source_lang=command.source_lang,
                target_lang=command.target_lang,
                status="running",
                current_stage=0,
                created_at=datetime.utcnow().isoformat(),
                updated_at=datetime.utcnow().isoformat(),
            )
            pipeline = await self._uow.pipelines.create(pipeline)

            # Create stage records
            stage_names = ["detect", "segment", "translate", "quality_check", "store"]
            for i, name in enumerate(stage_names):
                stage = PipelineStage(
                    id=None,
                    pipeline_id=pipeline_id,
                    name=name,
                    status="pending",
                    created_at=datetime.utcnow().isoformat(),
                    updated_at=datetime.utcnow().isoformat(),
                )
                await self._uow.pipeline_stages.create(stage)

            try:
                # Stage 1: Detect
                await self._update_stage_status(pipeline_id, "detect", "running")
                detect_result = await self.detect_language(DetectLanguageCommand(
                    text=command.source_text or "",
                    job_id=command.job_id,
                    work_id=command.work_id,
                    volume_id=command.volume_id,
                ))
                await self._update_stage_status(pipeline_id, "detect", "completed", output_data={"lang": detect_result.detected_lang})
                stages_completed.append("detect")

                # Stage 2: Segment
                await self._update_stage_status(pipeline_id, "segment", "running")
                segment_result = await self.segment_text(SegmentTextCommand(
                    text=command.source_text or "",
                    source_lang=command.source_lang,
                    target_lang=command.target_lang,
                    job_id=command.job_id,
                ))
                # Create segments in DB
                if segment_result.segments:
                    create_cmd = CreateSegmentsCommand(job_id=command.job_id, segments=segment_result.segments)
                    await self.create_segments(create_cmd)
                await self._update_stage_status(pipeline_id, "segment", "completed", output_data={"count": segment_result.total_segments})
                stages_completed.append("segment")

                # Stage 3: Translate
                await self._update_stage_status(pipeline_id, "translate", "running")
                translate_result = await self.translate_segments(TranslateSegmentsCommand(
                    job_id=command.job_id,
                    llm_provider="nvidia",  # Default, should come from job
                    model_name="meta/llama-3.1-70b-instruct",
                ))
                await self._update_stage_status(pipeline_id, "translate", "completed", output_data={"translated": translate_result.translated_count})
                stages_completed.append("translate")

                # Stage 4: Quality Check
                await self._update_stage_status(pipeline_id, "quality_check", "running")
                quality_result = await self.quality_check(QualityCheckCommand(
                    job_id=command.job_id,
                ))
                await self._update_stage_status(pipeline_id, "quality_check", "completed", output_data={"score": quality_result.overall_score})
                stages_completed.append("quality_check")

                # Stage 5: Store
                await self._update_stage_status(pipeline_id, "store", "running")
                store_result = await self.store_translations(StoreTranslationsCommand(
                    job_id=command.job_id,
                ))
                await self._update_stage_status(pipeline_id, "store", "completed", output_data={"stored": store_result.stored_count})
                stages_completed.append("store")

                # Mark pipeline complete
                pipeline.status = "completed"
                pipeline.current_stage = 5
                pipeline.updated_at = datetime.utcnow().isoformat()
                await self._uow.pipelines.update(pipeline)

                await self._uow.commit()

            except Exception as e:
                errors.append(str(e))
                # Mark pipeline failed
                pipeline.status = "failed"
                pipeline.updated_at = datetime.utcnow().isoformat()
                await self._uow.pipelines.update(pipeline)
                await self._uow.commit()
                raise

        duration_ms = int((time.time() - start_time) * 1000)

        return TranslationPipelineResult(
            pipeline_id=pipeline_id,
            job_id=command.job_id,
            stages_completed=stages_completed,
            stages_skipped=stages_skipped,
            errors=errors,
            duration_ms=duration_ms,
        )

    async def _update_stage_status(
        self,
        pipeline_id: str,
        stage_name: str,
        status: str,
        output_data: Optional[dict] = None,
        error_message: Optional[str] = None,
    ) -> None:
        """Update pipeline stage status."""
        stages = await self._uow.pipeline_stages.get_by_pipeline_id(pipeline_id)
        for stage in stages:
            if stage.name == stage_name:
                stage.status = status
                if output_data:
                    import json
                    stage.output_data = json.dumps(output_data)
                if error_message:
                    stage.error_message = error_message
                if status == "running" and not stage.started_at:
                    stage.started_at = datetime.utcnow().isoformat()
                elif status in ("completed", "failed"):
                    stage.completed_at = datetime.utcnow().isoformat()
                stage.updated_at = datetime.utcnow().isoformat()
                await self._uow.pipeline_stages.update(stage)
                break

    # =================== PIPELINE MANAGEMENT ===================

    async def get_pipeline_status(self, command: GetPipelineStatusCommand) -> dict:
        """Get pipeline status for a job."""
        pipeline = await self._uow.pipelines.get_by_job_id(command.job_id)
        if not pipeline:
            return {"job_id": command.job_id, "status": "not_found", "stages": []}

        stages = await self._uow.pipeline_stages.get_by_pipeline_id(pipeline.id)
        return {
            "job_id": command.job_id,
            "pipeline_id": pipeline.id,
            "status": pipeline.status,
            "current_stage": pipeline.current_stage,
            "stages": [
                {
                    "name": s.name,
                    "status": s.status,
                    "input_data": s.input_data,
                    "output_data": s.output_data,
                    "error_message": s.error_message,
                    "started_at": s.started_at,
                    "completed_at": s.completed_at,
                    "retry_count": s.retry_count,
                }
                for s in stages
            ],
        }

    async def resume_pipeline(self, command: ResumePipelineCommand) -> dict:
        """Resume a failed/paused pipeline from a specific stage."""
        pipeline = await self._uow.pipelines.get_by_job_id(command.job_id)
        if not pipeline:
            raise NotFoundError(f"No pipeline for job {command.job_id}")

        if pipeline.status not in ("failed", "paused", "running"):
            raise DomainError(f"Cannot resume pipeline in status {pipeline.status}")

        # Determine which stages to re-run
        stages = await self._uow.pipeline_stages.get_by_pipeline_id(pipeline.id)
        if command.from_stage:
            # Re-run from specified stage
            stage_order = ["detect", "segment", "translate", "quality_check", "store"]
            try:
                start_idx = stage_order.index(command.from_stage)
            except ValueError:
                raise DomainError(f"Invalid from_stage: {command.from_stage}")
            for stage in stages:
                if stage.name in stage_order[start_idx:]:
                    stage.status = "pending"
                    stage.error_message = None
                    await self._uow.pipeline_stages.update(stage)
        else:
            # Reset all failed/incomplete stages
            for stage in stages:
                if stage.status in ("failed", "running"):
                    stage.status = "pending"
                    stage.error_message = None
                    await self._uow.pipeline_stages.update(stage)

        pipeline.status = "running"
        await self._uow.pipelines.update(pipeline)
        await self._uow.commit()

        return await self.get_pipeline_status(GetPipelineStatusCommand(job_id=command.job_id))