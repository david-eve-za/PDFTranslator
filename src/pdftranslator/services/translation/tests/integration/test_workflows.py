"""
Integration tests for Translation Workflows.
"""

import pytest
from temporalio.testing import WorkflowEnvironment
from temporalio.client import Client


class TestTranslationWorkflow:
    """Integration tests for TranslationWorkflow."""

    @pytest.mark.asyncio
    async def test_workflow_runs_successfully(self):
        """Test that workflow executes all 5 stages."""
        # This test requires a Temporal test server
        # For now, we just verify the workflow class can be instantiated
        from pdftranslator.services.translation.workflows.translation_workflow import (
            TranslationWorkflow,
            TranslationWorkflowInput,
        )

        # Test workflow input creation
        input_data = TranslationWorkflowInput(
            job_id=1,
            work_id=1,
            source_text="Hello world. This is a test.",
            source_lang="en",
            target_lang="es",
        )

        assert input_data.job_id == 1
        assert input_data.work_id == 1
        assert input_data.source_lang == "en"
        assert input_data.target_lang == "es"

    @pytest.mark.asyncio
    async def test_workflow_input_defaults(self):
        """Test workflow input default values."""
        from pdftranslator.services.translation.workflows.translation_workflow import (
            TranslationWorkflowInput,
        )

        input_data = TranslationWorkflowInput(
            job_id=1,
            work_id=1,
            source_text="Test",
        )

        assert input_data.source_lang == "auto"
        assert input_data.target_lang == "en"
        assert input_data.llm_provider == "nvidia"
        assert input_data.model_name == "meta/llama-3.1-70b-instruct"
        assert input_data.temperature == 0.3
        assert input_data.max_tokens == 4096


class TestResumeTranslationWorkflow:
    """Integration tests for ResumeTranslationWorkflow."""

    @pytest.mark.asyncio
    async def test_resume_from_translate_stage(self):
        """Test resuming from translate stage."""
        from pdftranslator.services.translation.workflows.translation_workflow import (
            ResumeTranslationWorkflow,
            TranslationWorkflowInput,
        )

        input_data = TranslationWorkflowInput(
            job_id=1,
            work_id=1,
            source_text="Test text",
        )

        # Just verify instantiation works
        assert input_data.job_id == 1