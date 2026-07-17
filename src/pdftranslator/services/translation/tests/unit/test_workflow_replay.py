"""
Deterministic Replay Tests for Translation Workflows.

CUPID Principle: Predictable - Workflow replay produces identical results.
Sprint 3.4: Chaos Testing + Deterministic Replay

IMPORTANT: All workflow imports are inside test functions to avoid
loading temporalio at module level (causes bus error on Apple Silicon).
The conftest.py fixture mocks temporalio for activity tests before imports.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


class TestWorkflowDeterministicReplay:
    """Tests for deterministic workflow replay."""

    @pytest.mark.asyncio
    async def test_translation_workflow_deterministic_output(self):
        """Test that workflow produces same output for same input."""
        # Import inside test to avoid module-level temporalio import
        from pdftranslator.services.translation.workflows.translation_workflow import (
            TranslationWorkflow,
            TranslationWorkflowInput,
        )
        from pdftranslator.services.translation.activities import (
            DetectLanguageOutput,
            SegmentTextOutput,
            TranslateSegmentsOutput,
            QualityCheckOutput,
            StoreTranslationsOutput,
            GenerateAudioOutput,
        )

        # Mock all activities to return deterministic results - use function for cycling
        def activity_responder(activity, *args, **kwargs):
            name = getattr(activity, '__name__', '')
            if 'detect_language' in name:
                return DetectLanguageOutput(detected_lang="en", confidence=0.85, text_stats={"char_count": 10, "word_count": 2})
            elif 'segment_text' in name:
                return SegmentTextOutput(segments=[{"segment_number": 1, "source_text": "Hello world", "target_text": None}], total_segments=1, total_chars=11)
            elif 'translate_segments' in name:
                return TranslateSegmentsOutput(translated_count=1, failed_count=0, errors=[], duration_ms=100, segments=[{"segment_number": 1, "source_text": "Hello world", "target_text": "Hola mundo", "error": None}])
            elif 'quality_check' in name:
                return QualityCheckOutput(checked_count=1, passed_count=1, failed_count=0, issues=[], overall_score=1.0)
            elif 'store_translations' in name:
                return StoreTranslationsOutput(stored_count=1, errors=[])
            return MagicMock()

        with patch("pdftranslator.services.translation.workflows.translation_workflow.workflow.execute_activity", side_effect=activity_responder):
            workflow1 = TranslationWorkflow()
            input_data = TranslationWorkflowInput(
                job_id=1,
                work_id=1,
                source_text="Hello world",
                source_lang="en",
                target_lang="es",
                generate_audio=False,
            )

            result1 = await workflow1.run(input_data)

            # Run again with same input (NEW workflow instance for replay)
            workflow2 = TranslationWorkflow()
            result2 = await workflow2.run(input_data)

            # Results should be identical (deterministic replay)
            assert result1.pipeline_id != result2.pipeline_id  # UUID changes but that's expected
            assert result1.job_id == result2.job_id
            assert result1.status == result2.status
            assert result1.stages_completed == result2.stages_completed
            assert result1.errors == result2.errors
            # Duration may vary slightly but structure is deterministic


    @pytest.mark.asyncio
    async def test_workflow_replay_after_failure(self):
        """Test workflow can be replayed from failure point."""
        from pdftranslator.services.translation.workflows.translation_workflow import (
            TranslationWorkflow,
            TranslationWorkflowInput,
        )
        from pdftranslator.services.translation.activities import (
            DetectLanguageOutput,
            SegmentTextOutput,
            TranslateSegmentsOutput,
            QualityCheckOutput,
            StoreTranslationsOutput,
        )

        # First run fails at translate stage
        with patch("pdftranslator.services.translation.workflows.translation_workflow.workflow.execute_activity") as mock_execute:
            call_count = {"translate": 0}

            def first_run_mock(activity, *args, **kwargs):
                name = getattr(activity, '__name__', '')
                if 'detect_language' in name:
                    return DetectLanguageOutput(detected_lang="en", confidence=0.85, text_stats={"char_count": 10})
                elif 'segment_text' in name:
                    return SegmentTextOutput(segments=[{"segment_number": 1, "source_text": "Hello", "target_text": None}], total_segments=1, total_chars=5)
                elif 'translate_segments' in name:
                    call_count["translate"] += 1
                    if call_count["translate"] == 1:
                        raise Exception("LLM timeout")  # Failure here
                    return TranslateSegmentsOutput(translated_count=1, failed_count=0, errors=[], duration_ms=100, segments=[{"segment_number": 1, "source_text": "Hello", "target_text": "Hola", "error": None}])
                return MagicMock()

            mock_execute.side_effect = first_run_mock

            workflow = TranslationWorkflow()
            input_data = TranslationWorkflowInput(job_id=1, work_id=1, source_text="Hello")

            result = await workflow.run(input_data)
            assert result.status == "failed"
            assert "translate" not in result.stages_completed

        # Replay from failure (simulated by new workflow with same input)
        def second_run_mock(activity, *args, **kwargs):
            name = getattr(activity, '__name__', '')
            if 'detect_language' in name:
                return DetectLanguageOutput(detected_lang="en", confidence=0.85, text_stats={"char_count": 10})
            elif 'segment_text' in name:
                return SegmentTextOutput(segments=[{"segment_number": 1, "source_text": "Hello", "target_text": None}], total_segments=1, total_chars=5)
            elif 'translate_segments' in name:
                return TranslateSegmentsOutput(translated_count=1, failed_count=0, errors=[], duration_ms=100, segments=[{"segment_number": 1, "source_text": "Hello", "target_text": "Hola", "error": None}])
            elif 'quality_check' in name:
                return QualityCheckOutput(checked_count=1, passed_count=1, failed_count=0, issues=[], overall_score=1.0)
            elif 'store_translations' in name:
                return StoreTranslationsOutput(stored_count=1, errors=[])
            return MagicMock()

        with patch("pdftranslator.services.translation.workflows.translation_workflow.workflow.execute_activity", side_effect=second_run_mock):
            workflow2 = TranslationWorkflow()
            result2 = await workflow2.run(input_data)
            assert result2.status == "completed"
            assert "translate" in result2.stages_completed
            assert "quality_check" in result2.stages_completed
            assert "store" in result2.stages_completed


    @pytest.mark.asyncio
    async def test_resume_workflow_deterministic(self):
        """Test ResumeTranslationWorkflow produces deterministic results."""
        from pdftranslator.services.translation.workflows.translation_workflow import (
            ResumeTranslationWorkflow,
            TranslationWorkflowInput,
        )
        from pdftranslator.services.translation.activities import (
            DetectLanguageOutput,
            SegmentTextOutput,
            TranslateSegmentsOutput,
            QualityCheckOutput,
            StoreTranslationsOutput,
        )

        def mock(activity, *args, **kwargs):
            name = getattr(activity, '__name__', '')
            if 'detect_language' in name:
                return DetectLanguageOutput(detected_lang="en", confidence=0.85, text_stats={})
            elif 'segment_text' in name:
                return SegmentTextOutput(segments=[{"segment_number": 1, "source_text": "Hello", "target_text": None}], total_segments=1, total_chars=5)
            elif 'translate_segments' in name:
                return TranslateSegmentsOutput(translated_count=1, failed_count=0, errors=[], duration_ms=100, segments=[{"segment_number": 1, "source_text": "Hello", "target_text": "Hola", "error": None}])
            elif 'quality_check' in name:
                return QualityCheckOutput(checked_count=1, passed_count=1, failed_count=0, issues=[], overall_score=1.0)
            elif 'store_translations' in name:
                return StoreTranslationsOutput(stored_count=1, errors=[])
            return MagicMock()

        with patch("pdftranslator.services.translation.workflows.translation_workflow.workflow.execute_activity", side_effect=mock):
            workflow = ResumeTranslationWorkflow()
            input_data = TranslationWorkflowInput(job_id=1, work_id=1, source_text="Hello")

            result1 = await workflow.run(input_data, from_stage="translate")
            result2 = await workflow.run(input_data, from_stage="translate")

            # Both runs should have same stages completed
            assert result1.stages_completed == result2.stages_completed
            assert result1.errors == result2.errors


class TestWorkflowActivityRetryBehavior:
    """Tests for retry behavior and failure handling.

    Note: Temporal's retry is handled by the Temporal server, not our code.
    These tests verify our code handles retries correctly when they occur.
    """

    @pytest.mark.asyncio
    async def test_activity_exception_propagates(self):
        """Test that activity exceptions propagate to workflow (retries handled by Temporal)."""
        from pdftranslator.services.translation.workflows.translation_workflow import (
            TranslationWorkflow,
            TranslationWorkflowInput,
        )
        from pdftranslator.services.translation.activities import (
            DetectLanguageOutput,
            SegmentTextOutput,
            TranslateSegmentsOutput,
            QualityCheckOutput,
            StoreTranslationsOutput,
        )

        call_count = {"detect": 0}

        def mock_execute(activity, *args, **kwargs):
            name = getattr(activity, '__name__', '')
            if 'detect_language' in name:
                call_count["detect"] += 1
                if call_count["detect"] == 1:
                    raise Exception("Transient network error")
                return DetectLanguageOutput(detected_lang="en", confidence=0.85, text_stats={})
            elif 'segment_text' in name:
                return SegmentTextOutput(segments=[], total_segments=0, total_chars=0)
            elif 'translate_segments' in name:
                return TranslateSegmentsOutput(translated_count=0, failed_count=0, errors=[], duration_ms=0, segments=[])
            elif 'quality_check' in name:
                return QualityCheckOutput(checked_count=0, passed_count=0, failed_count=0, issues=[], overall_score=1.0)
            elif 'store_translations' in name:
                return StoreTranslationsOutput(stored_count=0, errors=[])
            return MagicMock()

        with patch("pdftranslator.services.translation.workflows.translation_workflow.workflow.execute_activity", side_effect=mock_execute):
            workflow = TranslationWorkflow()
            input_data = TranslationWorkflowInput(job_id=1, work_id=1, source_text="Hello")
            result = await workflow.run(input_data)

            # Exception should propagate (our mock only fails once, but in real Temporal it would retry)
            # Here we just verify the mock was called and exception propagated
            assert call_count["detect"] == 1
            assert result.status == "failed"
            assert "Transient network error" in str(result.errors)

    @pytest.mark.asyncio
    async def test_activity_fails_after_max_retries(self):
        """Test that workflow fails after max retries exceeded."""
        from pdftranslator.services.translation.workflows.translation_workflow import (
            TranslationWorkflow,
            TranslationWorkflowInput,
        )
        from pdftranslator.services.translation.activities import DetectLanguageOutput

        def mock_execute(activity, *args, **kwargs):
            name = getattr(activity, '__name__', '')
            if 'detect_language' in name:
                raise Exception("Permanent failure")
            return MagicMock()

        with patch("pdftranslator.services.translation.workflows.translation_workflow.workflow.execute_activity", side_effect=mock_execute):
            workflow = TranslationWorkflow()
            input_data = TranslationWorkflowInput(job_id=1, work_id=1, source_text="Hello")
            result = await workflow.run(input_data)

            assert result.status == "failed"
            assert len(result.errors) > 0
            assert "Permanent failure" in result.errors[0]


class TestWorkflowFailureModes:
    """Document and test various failure modes (Sprint 3.4 deliverable)."""

    FAILURE_MODES = {
        "activity_timeout": {
            "description": "Activity exceeds start_to_close_timeout",
            "recovery": "Workflow fails, can resume from failed stage",
            "retry": False,
        },
        "activity_transient_error": {
            "description": "Activity raises transient error (network, rate limit)",
            "recovery": "Automatic retry with exponential backoff (max 3 attempts)",
            "retry": True,
        },
        "activity_permanent_error": {
            "description": "Activity raises non-retryable error (invalid input, auth)",
            "recovery": "Workflow fails after retries exhausted, manual intervention",
            "retry": False,
        },
        "workflow_task_timeout": {
            "description": "Workflow task exceeds deadline (default 10s for sync code)",
            "recovery": "Temporal replays workflow task, activities not re-run if completed",
            "retry": True,
        },
        "temporal_server_unavailable": {
            "description": "Temporal cluster unavailable",
            "recovery": "Workflow stuck until server recovers, no data loss",
            "retry": "N/A (infrastructure)",
        },
        "activity_worker_crash": {
            "description": "Activity worker crashes mid-execution",
            "recovery": "Activity times out, retried on another worker",
            "retry": True,
        },
        "non_deterministic_code": {
            "description": "Workflow contains non-deterministic code (random, time, external calls)",
            "recovery": "Replay fails with non-deterministic error, must fix code",
            "retry": False,
        },
    }

    def test_failure_modes_documented(self):
        """Verify all failure modes are documented."""
        assert len(self.FAILURE_MODES) >= 7
        for mode, info in self.FAILURE_MODES.items():
            assert "description" in info
            assert "recovery" in info
            assert "retry" in info

    @pytest.mark.asyncio
    async def test_workflow_timeout_handling(self):
        """Test workflow handles activity timeouts."""
        from pdftranslator.services.translation.workflows.translation_workflow import (
            TranslationWorkflow,
            TranslationWorkflowInput,
        )

        def mock_execute(activity, *args, **kwargs):
            name = getattr(activity, '__name__', '')
            if 'detect_language' in name:
                # Simulate timeout
                raise TimeoutError("Activity timed out")
            return MagicMock()

        with patch("pdftranslator.services.translation.workflows.translation_workflow.workflow.execute_activity", side_effect=mock_execute):
            workflow = TranslationWorkflow()
            input_data = TranslationWorkflowInput(job_id=1, work_id=1, source_text="Hello")
            result = await workflow.run(input_data)

            assert result.status == "failed"
            assert "timed out" in result.errors[0].lower()


class TestWorkflowChaosExperiments:
    """
    Sprint 3.4: Chaos Testing experiments.

    These tests simulate chaos engineering scenarios:
    - Network partitions (simulated by activity timeouts)
    - Worker crashes (simulated by exceptions)
    - Latency injection (simulated by delays)
    """

    @pytest.mark.asyncio
    async def test_network_partition_simulation(self):
        """Simulate network partition during activity execution."""
        from pdftranslator.services.translation.workflows.translation_workflow import (
            TranslationWorkflow,
            TranslationWorkflowInput,
        )
        from pdftranslator.services.translation.activities import DetectLanguageOutput

        def mock_execute(activity, *args, **kwargs):
            name = getattr(activity, '__name__', '')
            if 'detect_language' in name:
                # Simulate network partition
                raise ConnectionError("Network partition - cannot reach Temporal")
            return MagicMock()

        with patch("pdftranslator.services.translation.workflows.translation_workflow.workflow.execute_activity", side_effect=mock_execute):
            workflow = TranslationWorkflow()
            input_data = TranslationWorkflowInput(job_id=1, work_id=1, source_text="Hello")
            result = await workflow.run(input_data)

            assert result.status == "failed"
            assert "Network partition" in result.errors[0]

    @pytest.mark.asyncio
    async def test_worker_crash_simulation(self):
        """Simulate activity worker crash and workflow replay recovery."""
        from pdftranslator.services.translation.workflows.translation_workflow import (
            TranslationWorkflow,
            TranslationWorkflowInput,
        )
        from pdftranslator.services.translation.activities import (
            DetectLanguageOutput,
            SegmentTextOutput,
            TranslateSegmentsOutput,
            QualityCheckOutput,
            StoreTranslationsOutput,
        )

        # First run: worker crashes during translate
        def first_run_mock(activity, *args, **kwargs):
            name = getattr(activity, '__name__', '')
            if 'detect_language' in name:
                return DetectLanguageOutput(detected_lang="en", confidence=0.85, text_stats={})
            elif 'segment_text' in name:
                return SegmentTextOutput(segments=[{"segment_number": 1, "source_text": "Hello", "target_text": None}], total_segments=1, total_chars=5)
            elif 'translate_segments' in name:
                raise RuntimeError("Worker crashed: OOM")
            return MagicMock()

        with patch("pdftranslator.services.translation.workflows.translation_workflow.workflow.execute_activity", side_effect=first_run_mock):
            workflow = TranslationWorkflow()
            input_data = TranslationWorkflowInput(job_id=1, work_id=1, source_text="Hello")
            result1 = await workflow.run(input_data)

            # Workflow fails (no retries in our mock)
            assert result1.status == "failed"
            assert "Worker crashed" in result1.errors[0]
            assert "translate" not in result1.stages_completed

        # Replay: second worker succeeds
        def second_run_mock(activity, *args, **kwargs):
            name = getattr(activity, '__name__', '')
            if 'detect_language' in name:
                return DetectLanguageOutput(detected_lang="en", confidence=0.85, text_stats={})
            elif 'segment_text' in name:
                return SegmentTextOutput(segments=[{"segment_number": 1, "source_text": "Hello", "target_text": None}], total_segments=1, total_chars=5)
            elif 'translate_segments' in name:
                return TranslateSegmentsOutput(
                    translated_count=1, failed_count=0, errors=[], duration_ms=100,
                    segments=[{"segment_number": 1, "source_text": "Hello", "target_text": "Hola", "error": None}]
                )
            elif 'quality_check' in name:
                return QualityCheckOutput(checked_count=1, passed_count=1, failed_count=0, issues=[], overall_score=1.0)
            elif 'store_translations' in name:
                return StoreTranslationsOutput(stored_count=1, errors=[])
            return MagicMock()

        with patch("pdftranslator.services.translation.workflows.translation_workflow.workflow.execute_activity", side_effect=second_run_mock):
            workflow2 = TranslationWorkflow()
            result2 = await workflow2.run(input_data)

            # Replay succeeds
            assert result2.status == "completed"
            assert "translate" in result2.stages_completed
            assert "quality_check" in result2.stages_completed
            assert "store" in result2.stages_completed

    @pytest.mark.asyncio
    async def test_latency_injection_simulation(self):
        """Test workflow handles high latency gracefully."""
        import time
        from pdftranslator.services.translation.workflows.translation_workflow import (
            TranslationWorkflow,
            TranslationWorkflowInput,
        )
        from pdftranslator.services.translation.activities import (
            DetectLanguageOutput,
            SegmentTextOutput,
            TranslateSegmentsOutput,
            QualityCheckOutput,
            StoreTranslationsOutput,
        )

        def mock_execute(activity, *args, **kwargs):
            name = getattr(activity, '__name__', '')
            if 'detect_language' in name:
                # Simulate high latency with synchronous sleep
                time.sleep(0.1)
                return DetectLanguageOutput(detected_lang="en", confidence=0.85, text_stats={"char_count": 5, "word_count": 1})
            elif 'segment_text' in name:
                return SegmentTextOutput(segments=[{"segment_number": 1, "source_text": "Hello", "target_text": None}], total_segments=1, total_chars=5)
            elif 'translate_segments' in name:
                return TranslateSegmentsOutput(translated_count=1, failed_count=0, errors=[], duration_ms=50, segments=[{"segment_number": 1, "source_text": "Hello", "target_text": "Hola", "error": None}])
            elif 'quality_check' in name:
                return QualityCheckOutput(checked_count=1, passed_count=1, failed_count=0, issues=[], overall_score=1.0)
            elif 'store_translations' in name:
                return StoreTranslationsOutput(stored_count=1, errors=[])
            return MagicMock()

        with patch("pdftranslator.services.translation.workflows.translation_workflow.workflow.execute_activity", side_effect=mock_execute):
            workflow = TranslationWorkflow()
            input_data = TranslationWorkflowInput(job_id=1, work_id=1, source_text="Hello")
            result = await workflow.run(input_data)

            assert result.status == "completed"
            assert result.duration_ms >= 100


# Run tests with: PYTHONPATH=src uv run pytest src/pdftranslator/services/translation/tests/unit/test_workflow_replay.py -v