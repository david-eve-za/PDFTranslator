"""
Pytest configuration for translation service unit tests.

Mocks temporalio to avoid Apple Silicon bus error in native bridge.
Provides proper awaitable mocks for workflow.execute_activity.
"""
import sys
from unittest.mock import MagicMock
import pytest


def pytest_configure(config):
    """Configure pytest - mock temporalio before any imports."""
    mock_temporalio = MagicMock()

    # activity.defn decorator
    mock_temporalio.activity = MagicMock()
    mock_temporalio.activity.defn = lambda x: x

    # workflow mocks
    mock_temporalio.workflow = MagicMock()
    mock_temporalio.workflow.defn = lambda x: x
    mock_temporalio.workflow.run = lambda x: x
    mock_temporalio.workflow.query = lambda x: x

    # execute_activity with proper await and exception handling
    async def mock_execute_activity(activity, *args, **kwargs):
        # Allow exceptions to propagate from tests
        return await _mock_execute_activity_impl(activity, *args, **kwargs)

    async def _mock_execute_activity_impl(activity, *args, **kwargs):
        if hasattr(activity, '__name__'):
            name = activity.__name__
            if 'detect_language' in name:
                return MagicMock(detected_lang="en", confidence=0.85, text_stats={})
            elif 'segment_text' in name:
                return MagicMock(segments=[], total_segments=0, total_chars=0)
            elif 'translate_segments' in name:
                return MagicMock(translated_count=0, failed_count=0, errors=[], duration_ms=0, segments=[])
            elif 'quality_check' in name:
                return MagicMock(checked_count=0, passed_count=0, failed_count=0, issues=[], overall_score=1.0)
            elif 'store_translations' in name:
                return MagicMock(stored_count=0, errors=[])
            elif 'generate_audio' in name:
                return MagicMock(audio_file_path=None, duration_ms=0, total_chars=0, errors=[])
        return MagicMock()

    mock_temporalio.workflow.execute_activity = mock_execute_activity
    mock_temporalio.workflow.unsafe = MagicMock()
    mock_temporalio.workflow.unsafe.imports_passed_through = MagicMock(
        return_value=MagicMock(__enter__=lambda self: None, __exit__=lambda self, *args: None)
    )
    mock_temporalio.workflow.logger = MagicMock()
    mock_temporalio.common = MagicMock()
    mock_temporalio.common.RetryPolicy = MagicMock()

    # Patch sys.modules
    for mod_name in ['temporalio', 'temporalio.activity', 'temporalio.workflow', 'temporalio.common',
                     'temporalio.bridge', 'temporalio.bridge.runtime', 'temporalio.bridge.client',
                     'temporalio.service', 'temporalio.converter', 'temporalio.client']:
        sys.modules[mod_name] = mock_temporalio


# Store the test-specific execute_activity implementations
_test_execute_activity_impl = None


def set_test_execute_activity(impl):
    """Override the execute_activity mock for specific tests."""
    global _test_execute_activity_impl
    _test_execute_activity_impl = impl


def clear_test_execute_activity():
    """Clear the test-specific execute_activity implementation."""
    global _test_execute_activity_impl
    _test_execute_activity_impl = None


# Note: Workflow tests use mocked temporalio which is sufficient for
# testing retry logic, failure handling, and deterministic behavior.
# For true replay testing, integration tests with real Temporal server needed.