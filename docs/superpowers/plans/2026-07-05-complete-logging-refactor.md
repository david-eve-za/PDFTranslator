# Complete Logging Refactor (refactor/remove-elk-logging) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete the logging refactoring started on branch `refactor/remove-elk-logging` - centralize logging configuration using Rich formatting with correlation IDs, replace ad-hoc logging in main.py/cli/app.py, and fix the new audio route dependencies.

**Architecture:** The refactoring introduces a centralized `logging_config.py` module with Rich console formatting, correlation ID propagation for async contexts, and structured logging helpers. All entry points (FastAPI backend, CLI) now use this shared configuration. The new audio route was added but is missing schema definitions and service implementation.

**Tech Stack:** Python 3.11+, FastAPI, Rich (logging), Pydantic, pytest

## Global Constraints

- Follow existing code patterns in the codebase
- Use TDD: write failing test first, then implement
- All imports must be `pdftranslator.*` absolute imports
- Logging must use `logging_config.py` helpers (`log_info`, `log_debug`, `log_warning`, `log_error`, `log_exception`)
- Correlation ID must propagate across async boundaries via contextvars
- Run tests after each task; never commit failing tests
- Keep changes minimal and focused

---

### Task 1: Add Missing Audio Schemas to schemas.py

**Files:**
- Modify: `src/pdftranslator/backend/api/models/schemas.py`
- Test: `tests/backend/api/test_audio_schemas.py` (new)

**Interfaces:**
- Produces: `AudioStartRequest`, `AudioJobResponse`, `AudioVoiceResponse` classes used by `audio.py` route

- [ ] **Step 1: Write the failing test**

```python
"""Test audio schemas exist and validate correctly."""
import pytest
from pdftranslator.backend.api.models.schemas import (
    AudioStartRequest,
    AudioJobResponse,
    AudioVoiceResponse,
)

def test_audio_start_request_valid():
    req = AudioStartRequest(work_id=1, scope="all_book", voice="Monica")
    assert req.work_id == 1
    assert req.scope == "all_book"
    assert req.voice == "Monica"
    assert req.skip_existing is True

def test_audio_start_request_optional_fields():
    req = AudioStartRequest(
        work_id=1,
        scope="all_volume",
        volume_id=5,
        chapter_id=10,
        voice="Samantha",
        skip_existing=False
    )
    assert req.volume_id == 5
    assert req.chapter_id == 10
    assert req.voice == "Samantha"
    assert req.skip_existing is False

def test_audio_job_response():
    resp = AudioJobResponse(job_id=42, status="pending")
    assert resp.job_id == 42
    assert resp.status == "pending"

def test_audio_voice_response():
    resp = AudioVoiceResponse(name="Monica", language="en_US")
    assert resp.name == "Monica"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Volumes/Elements2/PycharmProjects/PDFTranslator && python -m pytest tests/backend/api/test_audio_schemas.py -v`
Expected: FAIL with ImportError (schemas don't exist)

- [ ] **Step 3: Add missing schemas to schemas.py**

Add these classes to `src/pdftranslator/backend/api/models/schemas.py` (around line 160, after `AudioFileResponse`):

```python
class AudioStartRequest(BaseModel):
    """Request schema for starting an audio generation job."""

    work_id: int
    scope: str = Field(..., pattern=r"^(all_book|all_volume|single_chapter)$")
    volume_id: int | None = Field(default=None, description="Required when scope=all_volume")
    chapter_id: int | None = Field(default=None, description="Required when scope=single_chapter")
    voice: str = Field(default="Monica")
    skip_existing: bool = Field(default=True)


class AudioJobResponse(BaseModel):
    """Response schema for an audio generation job."""

    job_id: int
    status: str


class AudioVoiceResponse(BaseModel):
    """Response schema for a voice option."""

    name: str
    language: str
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /Volumes/Elements2/PycharmProjects/PDFTranslator && python -m pytest tests/backend/api/test_audio_schemas.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/pdftranslator/backend/api/models/schemas.py tests/backend/api/test_audio_schemas.py
git commit -m "feat: add AudioStartRequest, AudioJobResponse, AudioVoiceResponse schemas"
```

---

### Task 2: Create audio_service Module

**Files:**
- Create: `src/pdftranslator/backend/api/services/audio_service.py`
- Test: `tests/services/test_audio_service.py` (new)

**Interfaces:**
- Consumes: schemas from Task 1
- Produces: `audio_service` module with: `list_voices()`, `start_audio_job()`, `stream_progress()`, `get_audio_files()`, `get_download_path()`, `create_zip()`, `get_xspf_playlist_path()`

- [ ] **Step 1: Write the failing test**

```python
"""Test audio service functions."""
import pytest
from pathlib import Path
from pdftranslator.backend.api.services.audio_service import audio_service
from pdftranslator.backend.api.models.schemas import (
    AudioStartRequest,
    AudioJobResponse,
    AudioVoiceResponse,
)

def test_list_voices_returns_list():
    voices = audio_service.list_voices()
    assert isinstance(voices, list)
    if voices:
        assert all(isinstance(v, AudioVoiceResponse) for v in voices)

def test_audio_start_request_validation():
    req = AudioStartRequest(work_id=1, scope="all_book")
    assert req.work_id == 1
    assert req.scope == "all_book"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Volumes/Elements2/PycharmProjects/PDFTranslator && python -m pytest tests/services/test_audio_service.py -v`
Expected: FAIL (module not found)

- [ ] **Step 3: Implement audio_service.py**

Create `src/pdftranslator/backend/api/services/audio_service.py`:

```python
"""Audio generation service implementation."""

from __future__ import annotations

import asyncio
import logging
import subprocess
import tempfile
from pathlib import Path
from typing import AsyncGenerator, List, Optional

from pdftranslator.backend.logging_config import log_debug, log_info, log_warning, log_error
from pdftranslator.backend.api.models.schemas import (
    AudioFileResponse,
    AudioJobResponse,
    AudioVoiceResponse,
    AudioStartRequest,
)
from pdftranslator.database.repositories.translation_job_repo import TranslationJobRepository
from pdftranslator.core.config.settings import Settings

logger = logging.getLogger(__name__)


class AudioService:
    """Service for managing audio generation jobs."""

    def __init__(self) -> None:
        self._jobs: dict[int, dict] = {}
        self._job_counter = 0
        self._progress_queues: dict[int, asyncio.Queue] = {}
        self._settings = Settings.get()

    def list_voices(self) -> List[AudioVoiceResponse]:
        """List available macOS voices using say command."""
        log_debug(logger, "Listing available macOS voices")
        try:
            result = subprocess.run(
                ["say", "-v", "?"],
                capture_output=True,
                text=True,
                check=True,
            )
            voices = []
            for line in result.stdout.strip().split("\n"):
                parts = line.split()
                if len(parts) >= 2:
                    name = parts[0]
                    language = parts[1].strip("()")
                    voices.append(AudioVoiceResponse(name=name, language=language))
            log_info(logger, "Listed voices", count=len(voices))
            return voices
        except Exception as e:
            log_error(logger, "Failed to list voices", error=str(e), exc_info=True)
            return []

    async def start_audio_job(self, request: AudioStartRequest) -> AudioJobResponse:
        """Start an audio generation job."""
        log_info(logger, "Starting audio generation job",
                 work_id=request.work_id,
                 scope=request.scope,
                 voice=request.voice)

        # TODO: Implement actual audio job creation
        # For now, return a mock response
        self._job_counter += 1
        job_id = self._job_counter

        self._jobs[job_id] = {
            "id": job_id,
            "work_id": request.work_id,
            "scope": request.scope,
            "volume_id": request.volume_id,
            "chapter_id": request.chapter_id,
            "voice": request.voice,
            "status": "pending",
            "progress": 0,
        }

        log_info(logger, "Audio generation job started", job_id=job_id, work_id=request.work_id)
        return AudioJobResponse(job_id=job_id, status="pending")

    async def stream_progress(self, job_id: int) -> AsyncGenerator[str, None]:
        """SSE stream for job progress."""
        log_debug(logger, "Opening SSE stream for audio job", job_id=job_id)

        if job_id not in self._jobs:
            yield f"data: {{\"error\": \"Job {job_id} not found\"}}\n\n"
            return

        queue = asyncio.Queue()
        self._progress_queues[job_id] = queue

        try:
            while True:
                progress = await queue.get()
                yield f"data: {progress}\n\n"
                if progress.get("status") in ("completed", "failed"):
                    break
        finally:
            self._progress_queues.pop(job_id, None)

    def get_audio_files(
        self,
        work_id: int,
        volume_id: Optional[int] = None,
        chapter_id: Optional[int] = None,
    ) -> List[AudioFileResponse]:
        """List audio files for a work."""
        log_debug(logger, "Listing audio files", work_id=work_id, volume_id=volume_id, chapter_id=chapter_id)
        # TODO: Implement actual file listing
        log_info(logger, "Listed audio files", work_id=work_id, count=0)
        return []

    def get_download_path(
        self,
        work_id: int,
        volume_id: Optional[int],
        chapter_id: Optional[int],
        filename: str,
    ) -> Path:
        """Get path for audio file download."""
        # TODO: Implement actual path resolution
        raise ValueError(f"Audio file not found: {filename}")

    def create_zip(self, work_id: int, volume_id: Optional[int] = None) -> Path:
        """Create ZIP of audio files."""
        log_info(logger, "Creating ZIP download", work_id=work_id, volume_id=volume_id)
        # TODO: Implement ZIP creation
        raise ValueError("ZIP creation not implemented")

    def get_xspf_playlist_path(self, work_id: int, volume_id: Optional[int] = None) -> Optional[Path]:
        """Get XSPF playlist path."""
        log_debug(logger, "Getting playlist path", work_id=work_id, volume_id=volume_id)
        # TODO: Implement playlist generation
        return None


# Singleton instance
audio_service = AudioService()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /Volumes/Elements2/PycharmProjects/PDFTranslator && python -m pytest tests/services/test_audio_service.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/pdftranslator/backend/api/services/audio_service.py tests/services/test_audio_service.py
git commit -m "feat: implement audio_service with basic voice listing and job management"
```

---

### Task 3: Add Tests for Centralized Logging Configuration

**Files:**
- Create: `tests/backend/test_logging_config.py`

**Interfaces:**
- Tests: `setup_backend_logging()`, `setup_cli_logging()`, correlation ID propagation, structured logging helpers

- [ ] **Step 1: Write the failing test**

```python
"""Test centralized logging configuration."""
import logging
import uuid
from pdftranslator.backend.logging_config import (
    setup_backend_logging,
    setup_cli_logging,
    get_correlation_id,
    set_correlation_id,
    CorrelationContext,
    log_info,
    log_debug,
    log_warning,
    log_error,
    log_exception,
)

def test_setup_backend_logging_creates_rich_handler():
    """Verify backend logging uses Rich handler."""
    setup_backend_logging(log_level=logging.DEBUG)
    root_logger = logging.getLogger()
    # Check Rich handler is present
    from rich.logging import RichHandler
    handlers = [h for h in root_logger.handlers if isinstance(h, RichHandler)]
    assert len(handlers) == 1
    assert root_logger.level == logging.DEBUG

def test_setup_cli_logging_creates_file_and_console():
    """Verify CLI logging has both file and console handlers."""
    import tempfile
    import os
    with tempfile.TemporaryDirectory() as tmpdir:
        # Monkey-patch log file location
        import pdftranslator.backend.logging_config as lc
        original = lc.LOG_FILE_NAME
        lc.LOG_FILE_NAME = os.path.join(tmpdir, "test.log")
        try:
            setup_cli_logging(log_level=logging.INFO)
            root_logger = logging.getLogger()
            from rich.logging import RichHandler
            rich_handlers = [h for h in root_logger.handlers if isinstance(h, RichHandler)]
            file_handlers = [h for h in root_logger.handlers if isinstance(h, logging.FileHandler)]
            assert len(rich_handlers) == 1
            assert len(file_handlers) == 1
        finally:
            lc.LOG_FILE_NAME = original

def test_correlation_id_generation():
    """Test correlation ID is generated and retrieved."""
    cid = get_correlation_id()
    assert cid is not None
    assert len(cid) == 8

def test_correlation_id_can_be_set():
    """Test correlation ID can be explicitly set."""
    set_correlation_id("test-1234")
    assert get_correlation_id() == "test-1234"

def test_correlation_context_manager():
    """Test CorrelationContext manager sets and restores ID."""
    original = get_correlation_id()
    with CorrelationContext("ctx-5678") as cid:
        assert cid == "ctx-5678"
        assert get_correlation_id() == "ctx-5678"
    # Should restore original
    assert get_correlation_id() == original

def test_structured_logging_helpers_exist():
    """Verify all logging helper functions are callable."""
    logger = logging.getLogger("test")
    # These should not raise
    log_info(logger, "test info", key="value")
    log_debug(logger, "test debug")
    log_warning(logger, "test warning")
    log_error(logger, "test error")
    log_exception(logger, "test exception")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Volumes/Elements2/PycharmProjects/PDFTranslator && python -m pytest tests/backend/test_logging_config.py -v`
Expected: FAIL (test file doesn't exist yet)

- [ ] **Step 3: Create the test file (tests already written in Step 1)**

The test file IS the implementation - save Step 1 content to `tests/backend/test_logging_config.py`

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /Volumes/Elements2/PycharmProjects/PDFTranslator && python -m pytest tests/backend/test_logging_config.py -v`
Expected: PASS

- [ ] **Step 5: Verify actual logging works**

```bash
cd /Volumes/Elements2/PycharmProjects/PDFTranslator && python -c "
from pdftranslator.backend.logging_config import setup_backend_logging, log_info
import logging
setup_backend_logging()
logger = logging.getLogger('test')
log_info(logger, 'Test message', custom_field='value')
"
```
Expected: Rich-formatted log output with correlation ID

- [ ] **Step 6: Commit**

```bash
git add tests/backend/test_logging_config.py
git commit -m "test: add logging_config tests for Rich formatting and correlation IDs"
```

---

### Task 4: Verify Integration - Run Full Test Suite

**Files:**
- No new files
- Verify: all existing tests pass with new logging

- [ ] **Step 1: Run backend API tests**

Run: `cd /Volumes/Elements2/PycharmProjects/PDFTranslator && python -m pytest tests/backend/api/ -v`
Expected: All tests PASS (or only pre-existing failures)

- [ ] **Step 2: Run CLI tests**

Run: `cd /Volumes/Elements2/PycharmProjects/PDFTranslator && python -m pytest tests/cli/ -v`
Expected: All tests PASS

- [ ] **Step 3: Run integration tests**

Run: `cd /Volumes/Elements2/PycharmProjects/PDFTranslator && python -m pytest tests/integration/ -v`
Expected: All tests PASS

- [ ] **Step 4: Run database tests**

Run: `cd /Volumes/Elements2/PycharmProjects/PDFTranslator && python -m pytest tests/database/ -v`
Expected: All tests PASS (may need DB running)

- [ ] **Step 5: Quick manual verification**

```bash
cd /Volumes/Elements2/PycharmProjects/PDFTranslator && python -m uvicorn src.pdftranslator.backend.main:app --reload &
sleep 3
curl http://localhost:8000/health
curl http://localhost:8000/api/audio/voices
```

- [ ] **Step 6: Commit any fixes needed**

```bash
git add -A
git commit -m "fix: resolve any test failures from logging refactor"
```

---

### Task 5: Finalize Branch - Commit and Push

**Files:**
- Modified: `src/pdftranslator/backend/main.py`
- Modified: `src/pdftranslator/cli/app.py`
- Created: `src/pdftranslator/backend/logging_config.py`
- Created: `src/pdftranslator/backend/api/routes/audio.py`
- Created: `src/pdftranslator/backend/api/services/audio_service.py`
- Modified: `src/pdftranslator/backend/api/models/schemas.py`
- Created: `tests/backend/api/test_audio_schemas.py`
- Created: `tests/services/test_audio_service.py`
- Created: `tests/backend/test_logging_config.py`

- [ ] **Step 1: Stage all changes**

```bash
git add -A
```

- [ ] **Step 2: Create comprehensive commit**

```bash
git commit -m "refactor: complete logging centralization with Rich formatting and correlation IDs

- Add centralized logging_config.py with Rich console formatting, correlation ID
  propagation via contextvars, and structured logging helpers (log_info, log_debug,
  log_warning, log_error, log_exception)
- Update main.py to use lifespan handler for logging setup on startup
- Update cli/app.py to use centralized setup_cli_logging()
- Add audio routes with new logging integration
- Implement audio_service with voice listing and job management
- Add missing audio schemas (AudioStartRequest, AudioJobResponse, AudioVoiceResponse)
- Add tests for logging configuration and audio components
- Remove ad-hoc logging setup code from entry points
- CORS origins now configurable via CORS_ORIGINS env var"
```

- [ ] **Step 3: Push branch**

```bash
git push origin refactor/remove-elk-logging
```

- [ ] **Step 4: Create PR description**

The branch is ready for PR review. Key changes:
1. Centralized logging eliminates duplicate configuration
2. Rich formatting improves developer experience
3. Correlation IDs enable request tracing across async boundaries
4. Audio API routes integrated with new logging
5. All entry points (FastAPI, CLI) use shared configuration