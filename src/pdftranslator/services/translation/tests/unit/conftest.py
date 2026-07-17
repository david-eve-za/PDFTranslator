"""
Pytest configuration for translation service unit tests.

Mocks temporalio to avoid Apple Silicon bus error in native bridge.
"""
import sys
from unittest.mock import MagicMock


def pytest_configure(config):
    """Configure pytest with temporalio mocking before any tests run."""
    # Mock temporalio before any imports
    mock_temporalio = MagicMock()
    mock_temporalio.activity = MagicMock()
    mock_temporalio.activity.defn = lambda x: x  # Decorator passthrough
    mock_temporalio.workflow = MagicMock()
    mock_temporalio.workflow.defn = lambda x: x
    mock_temporalio.workflow.run = lambda x: x
    mock_temporalio.workflow.query = lambda x: x
    mock_temporalio.workflow.execute_activity = MagicMock()
    mock_temporalio.workflow.unsafe = MagicMock()
    mock_temporalio.workflow.unsafe.imports_passed_through = MagicMock(
        return_value=MagicMock(__enter__=lambda self: None, __exit__=lambda self, *args: None)
    )
    mock_temporalio.workflow.logger = MagicMock()
    mock_temporalio.common = MagicMock()
    mock_temporalio.common.RetryPolicy = MagicMock()

    sys.modules['temporalio'] = mock_temporalio
    sys.modules['temporalio.activity'] = mock_temporalio.activity
    sys.modules['temporalio.workflow'] = mock_temporalio.workflow
    sys.modules['temporalio.common'] = mock_temporalio.common
    sys.modules['temporalio.bridge'] = MagicMock()
    sys.modules['temporalio.bridge.runtime'] = MagicMock()
    sys.modules['temporalio.bridge.client'] = MagicMock()
    sys.modules['temporalio.service'] = MagicMock()
    sys.modules['temporalio.converter'] = MagicMock()
    sys.modules['temporalio.client'] = MagicMock()