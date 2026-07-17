"""
Translation Workflows for Temporal.

CUPID Principle: Predictable - Deterministic workflow execution with replay.
CUPID Principle: Domain-Focused - Models translation job lifecycle.
CUPID Principle: Composable - Workflows compose activities.
CUPID Principle: Unix Philosophy - Each workflow/activity has single responsibility.
"""

import time
import uuid
from dataclasses import dataclass
from datetime import timedelta

from temporalio import workflow
from temporalio.common import RetryPolicy

# Import activities for type hints - use unsafe imports for workflow
with workflow.unsafe.imports_passed_through():
    from pdftranslator.services.translation.activities import (
        DetectLanguageInput,
        DetectLanguageOutput,
        GenerateAudioInput,
        GenerateAudioOutput,
        QualityCheckInput,
        QualityCheckOutput,
        SegmentTextInput,
        SegmentTextOutput,
        StoreTranslationsInput,
        StoreTranslationsOutput,
        TranslateSegmentsInput,
        TranslateSegmentsOutput,
        detect_language_activity,
        generate_audio_activity,
        quality_check_activity,
        segment_text_activity,
        store_translations_activity,
        translate_segments_activity,
    )


@dataclass
class TranslationWorkflowInput:
    """Input for translation workflow."""
    job_id: int
    work_id: int
    volume_id: int | None = None
    source_text: str = ""
    source_lang: str = "auto"
    target_lang: str = "en"
    llm_provider: str = "nvidia"
    model_name: str = "meta/llama-3.1-70b-instruct"
    temperature: float = 0.3
    max_tokens: int = 4096
    max_segment_length: int = 5000
    quality_check_types: list[str] = None
    # Audio generation options (Stage 6)
    generate_audio: bool = False
    audio_voice: str = "Samantha"
    audio_format: str = "m4a"
    audio_sample_rate: int = 24000
    audio_bitrate: str = "48k"
    audio_normalize: bool = True
    audio_target_loudness: float = -16.0
    audio_engine: str = "macos-say"


@dataclass
class TranslationWorkflowOutput:
    """Output for translation workflow."""
    pipeline_id: str
    job_id: int
    status: str
    stages_completed: list[str]
    errors: list[str]
    duration_ms: int
    audio_file_path: str | None = None
    audio_duration_ms: int = 0


# Default quality checks
DEFAULT_QUALITY_CHECKS = ["completeness", "fluency", "consistency", "formatting"]


@workflow.defn
class TranslationWorkflow:
    """
    Temporal Workflow for Translation Jobs.

    Orchestrates the 5-stage translation pipeline:
    1. Detect Language
    2. Segment Text
    3. Translate Segments
    4. Quality Check
    5. Store Translations

    CUPID: Predictable - Workflow is deterministic and replayable.
    CUPID: Domain-Focused - Models the translation job lifecycle.
    """

    def __init__(self):
        self._pipeline_id = str(uuid.uuid4())
        self._stages_completed: list[str] = []
        self._errors: list[str] = []
        self._status = "pending"

    @workflow.run
    async def run(self, input_data: TranslationWorkflowInput) -> TranslationWorkflowOutput:
        """Execute the full translation pipeline."""
        start_time = time.time()
        self._status = "running"

        # Use defaults for quality checks
        quality_checks = input_data.quality_check_types or DEFAULT_QUALITY_CHECKS

        # Activity options - all activities have 10 min timeout with retry
        activity_options = {
            "start_to_close_timeout": timedelta(minutes=10),
            "retry_policy": RetryPolicy(
                initial_interval=timedelta(seconds=1),
                maximum_interval=timedelta(minutes=5),
                maximum_attempts=3,
            ),
        }

        try:
            # Stage 1: Detect Language
            self._status = "detecting_language"
            detect_result: DetectLanguageOutput = await workflow.execute_activity(
                detect_language_activity,
                DetectLanguageInput(
                    text=input_data.source_text,
                    job_id=input_data.job_id,
                    work_id=input_data.work_id,
                ),
                **activity_options,
            )
            self._stages_completed.append("detect")
            workflow.logger.info(f"Language detected: {detect_result.detected_lang}")

            # Use detected language if source_lang is auto
            detected_lang = detect_result.detected_lang
            source_lang = input_data.source_lang if input_data.source_lang != "auto" else detected_lang

            # Stage 2: Segment Text
            self._status = "segmenting_text"
            segment_result: SegmentTextOutput = await workflow.execute_activity(
                segment_text_activity,
                SegmentTextInput(
                    text=input_data.source_text,
                    source_lang=source_lang,
                    target_lang=input_data.target_lang,
                    job_id=input_data.job_id,
                    max_segment_length=input_data.max_segment_length,
                    split_by_sentences=True,
                ),
                **activity_options,
            )
            self._stages_completed.append("segment")
            workflow.logger.info(f"Created {segment_result.total_segments} segments")

            # Stage 3: Translate Segments
            self._status = "translating_segments"
            translate_result: TranslateSegmentsOutput = await workflow.execute_activity(
                translate_segments_activity,
                TranslateSegmentsInput(
                    job_id=input_data.job_id,
                    segments=segment_result.segments,
                    source_lang=source_lang,
                    target_lang=input_data.target_lang,
                    llm_provider=input_data.llm_provider,
                    model_name=input_data.model_name,
                    temperature=input_data.temperature,
                    max_tokens=input_data.max_tokens,
                ),
                **activity_options,
            )
            self._stages_completed.append("translate")
            if translate_result.errors:
                self._errors.extend(translate_result.errors)
            workflow.logger.info(f"Translated {translate_result.translated_count} segments")

            # Stage 4: Quality Check
            self._status = "quality_checking"
            quality_result: QualityCheckOutput = await workflow.execute_activity(
                quality_check_activity,
                QualityCheckInput(
                    segments=translate_result.segments,
                    source_lang=source_lang,
                    target_lang=input_data.target_lang,
                    check_types=quality_checks,
                    threshold=0.7,
                ),
                **activity_options,
            )
            self._stages_completed.append("quality_check")
            workflow.logger.info(f"Quality check: {quality_result.passed_count}/{quality_result.checked_count} passed, score={quality_result.overall_score:.2f}")

            # Stage 5: Store Translations
            self._status = "storing_translations"
            store_result: StoreTranslationsOutput = await workflow.execute_activity(
                store_translations_activity,
                StoreTranslationsInput(
                    job_id=input_data.job_id,
                    segments=translate_result.segments,
                    pipeline_id=self._pipeline_id,
                ),
                **activity_options,
            )
            self._stages_completed.append("store")
            if store_result.errors:
                self._errors.extend(store_result.errors)
            workflow.logger.info(f"Stored {store_result.stored_count} translations")

            # Stage 6: Generate Audio (optional)
            audio_file_path = None
            audio_duration_ms = 0
            if input_data.generate_audio:
                self._status = "generating_audio"
                audio_result: GenerateAudioOutput = await workflow.execute_activity(
                    generate_audio_activity,
                    GenerateAudioInput(
                        job_id=input_data.job_id,
                        segments=translate_result.segments,
                        target_lang=input_data.target_lang,
                        voice=input_data.audio_voice,
                        format=input_data.audio_format,
                        sample_rate=input_data.audio_sample_rate,
                        bitrate=input_data.audio_bitrate,
                        normalize=input_data.audio_normalize,
                        target_loudness=input_data.audio_target_loudness,
                        engine=input_data.audio_engine,
                    ),
                    **activity_options,
                )
                self._stages_completed.append("generate_audio")
                if audio_result.errors:
                    self._errors.extend(audio_result.errors)
                audio_file_path = audio_result.audio_file_path
                audio_duration_ms = audio_result.duration_ms
                workflow.logger.info(f"Generated audio: {audio_file_path} ({audio_duration_ms}ms)")

            self._status = "completed"
            duration_ms = int((time.time() - start_time) * 1000)

            return TranslationWorkflowOutput(
                pipeline_id=self._pipeline_id,
                job_id=input_data.job_id,
                status=self._status,
                stages_completed=self._stages_completed,
                errors=self._errors,
                duration_ms=duration_ms,
                audio_file_path=audio_file_path,
                audio_duration_ms=audio_duration_ms,
            )

        except Exception as e:
            self._status = "failed"
            self._errors.append(str(e))
            workflow.logger.error(f"Workflow failed: {e}")
            duration_ms = int((time.time() - start_time) * 1000)

            return TranslationWorkflowOutput(
                pipeline_id=self._pipeline_id,
                job_id=input_data.job_id,
                status=self._status,
                stages_completed=self._stages_completed,
                errors=self._errors,
                duration_ms=duration_ms,
            )

    @workflow.query
    def get_status(self) -> dict:
        """Query current workflow status."""
        return {
            "pipeline_id": self._pipeline_id,
            "status": self._status,
            "stages_completed": self._stages_completed,
            "errors": self._errors,
        }


@workflow.defn
class ResumeTranslationWorkflow:
    """
    Temporal Workflow for Resuming Failed Translation Pipelines.

    Re-runs pipeline from a specific failed stage.
    """

    def __init__(self):
        self._pipeline_id = str(uuid.uuid4())
        self._stages_completed: list[str] = []
        self._errors: list[str] = []
        self._status = "pending"

    @workflow.run
    async def run(
        self,
        input_data: TranslationWorkflowInput,
        from_stage: str = "detect",
    ) -> TranslationWorkflowOutput:
        """Execute translation pipeline from a specific stage."""
        start_time = time.time()
        self._status = "running"

        quality_checks = input_data.quality_check_types or DEFAULT_QUALITY_CHECKS

        # Define stage order
        stage_order = ["detect", "segment", "translate", "quality_check", "store"]
        try:
            start_idx = stage_order.index(from_stage)
        except ValueError:
            raise ValueError(f"Invalid from_stage: {from_stage}") from None

        stages_to_run = stage_order[start_idx:]

        # Activity options
        activity_options = {
            "start_to_close_timeout": timedelta(minutes=10),
            "retry_policy": RetryPolicy(
                initial_interval=timedelta(seconds=1),
                maximum_interval=timedelta(minutes=5),
                maximum_attempts=3,
            ),
        }

        try:
            # We need to pass along intermediate results between stages
            # In a real implementation, these would come from persisted state
            # For now, we run the full pipeline but skip completed stages

            detect_result = None
            segment_result = None
            translate_result = None

            if "detect" in stages_to_run:
                self._status = "detecting_language"
                detect_result = await workflow.execute_activity(
                    detect_language_activity,
                    DetectLanguageInput(
                        text=input_data.source_text,
                        job_id=input_data.job_id,
                        work_id=input_data.work_id,
                    ),
                    **activity_options,
                )
                self._stages_completed.append("detect")

            source_lang = input_data.source_lang
            if source_lang == "auto" and detect_result:
                source_lang = detect_result.detected_lang

            if "segment" in stages_to_run:
                self._status = "segmenting_text"
                segment_result = await workflow.execute_activity(
                    segment_text_activity,
                    SegmentTextInput(
                        text=input_data.source_text,
                        source_lang=source_lang,
                        target_lang=input_data.target_lang,
                        job_id=input_data.job_id,
                        max_segment_length=input_data.max_segment_length,
                        split_by_sentences=True,
                    ),
                    **activity_options,
                )
                self._stages_completed.append("segment")

            if "translate" in stages_to_run:
                self._status = "translating_segments"
                # Need segments from segment_result or previous state
                segments = segment_result.segments if segment_result else []
                translate_result = await workflow.execute_activity(
                    translate_segments_activity,
                    TranslateSegmentsInput(
                        job_id=input_data.job_id,
                        segments=segments,
                        source_lang=source_lang,
                        target_lang=input_data.target_lang,
                        llm_provider=input_data.llm_provider,
                        model_name=input_data.model_name,
                        temperature=input_data.temperature,
                        max_tokens=input_data.max_tokens,
                    ),
                    **activity_options,
                )
                self._stages_completed.append("translate")
                if translate_result.errors:
                    self._errors.extend(translate_result.errors)

            if "quality_check" in stages_to_run:
                self._status = "quality_checking"
                segments = translate_result.segments if translate_result else []
                await workflow.execute_activity(
                    quality_check_activity,
                    QualityCheckInput(
                        segments=segments,
                        source_lang=source_lang,
                        target_lang=input_data.target_lang,
                        check_types=quality_checks,
                        threshold=0.7,
                    ),
                    **activity_options,
                )
                self._stages_completed.append("quality_check")

            if "store" in stages_to_run:
                self._status = "storing_translations"
                segments = translate_result.segments if translate_result else []
                store_result = await workflow.execute_activity(
                    store_translations_activity,
                    StoreTranslationsInput(
                        job_id=input_data.job_id,
                        segments=segments,
                        pipeline_id=self._pipeline_id,
                    ),
                    **activity_options,
                )
                self._stages_completed.append("store")
                if store_result.errors:
                    self._errors.extend(store_result.errors)

            self._status = "completed"
            duration_ms = int((time.time() - start_time) * 1000)

            return TranslationWorkflowOutput(
                pipeline_id=self._pipeline_id,
                job_id=input_data.job_id,
                status=self._status,
                stages_completed=self._stages_completed,
                errors=self._errors,
                duration_ms=duration_ms,
            )

        except Exception as e:
            self._status = "failed"
            self._errors.append(str(e))
            duration_ms = int((time.time() - start_time) * 1000)

            return TranslationWorkflowOutput(
                pipeline_id=self._pipeline_id,
                job_id=input_data.job_id,
                status=self._status,
                stages_completed=self._stages_completed,
                errors=self._errors,
                duration_ms=duration_ms,
            )

    @workflow.query
    def get_status(self) -> dict:
        """Query current workflow status."""
        return {
            "pipeline_id": self._pipeline_id,
            "status": self._status,
            "stages_completed": self._stages_completed,
            "errors": self._errors,
        }
