# SOLID Refactoring Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Refactor PDFTranslator to comply with SOLID principles using incremental strangler fig approach, creating a clean architecture with 4 layers (Domain → Application → Infrastructure → Presentation) without breaking external behavior.

**Architecture:** Create domain layer (models, protocols, exceptions) first, then make infrastructure implement those protocols, then create application services that orchestrate use cases, and finally adapt presentation (CLI + Backend) to use application services. Legacy code is kept with re-exports until Phase 5 elimination.

**Tech Stack:** Python 3.11, Pydantic, Protocols (typing), psycopg, FastAPI, Typer, pytest

**Design Doc:** `docs/plans/2026-04-22-solid-refactoring-design.md`

---

## Phase 0: Preparation

### Task 0.1: Create Safety Tag and Branch

**Files:**
- None (git operations only)

**Step 1: Create safety tag**
```bash
git tag -a refactor-safe-point -m "Estado estable pre-refactorización SOLID"
git push origin refactor-safe-point
```

**Step 2: Create refactor branch**
```bash
git checkout -b refactor/solid-phase-0
```

**Step 3: Verify tag exists**
```bash
git tag -l "refactor-safe-point"
```
Expected: `refactor-safe-point`

**Step 4: Commit**
Already on new branch, no commit needed yet.

---

### Task 0.2: Record Test Baseline

**Files:**
- Create: `docs/plans/refactor-baseline.md`

**Step 1: Run existing tests and capture output**
```bash
cd /Volumes/Elements2/PycharmProjects/PDFTranslator
python -m pytest tests/ --tb=short -q --co 2>/dev/null | wc -l > /tmp/test_count.txt
python -m pytest tests/ --tb=short -q 2>&1 | tee /tmp/test_results.txt
```

**Step 2: Run coverage if available**
```bash
python -m pytest tests/ --cov=src/pdftranslator --cov-report=term-missing --tb=short -q 2>&1 | tee /tmp/coverage_results.txt || echo "Coverage not available, skipping"
```

**Step 3: Create baseline document**
```markdown
# Refactoring Baseline Metrics

**Date:** 2026-04-22
**Tag:** refactor-safe-point

## Test Results
[Paste /tmp/test_results.txt content here]

## Coverage
[Paste /tmp/coverage_results.txt content here or "N/A"]

## Known Issues
- Some tests require NVIDIA_API_KEY (skipped)
- Some tests require database (integration)
- Coverage tool may not be configured
```

**Step 4: Save to file**
Write the document to `docs/plans/refactor-baseline.md`

**Step 5: Commit**
```bash
git add docs/plans/refactor-baseline.md
git commit -m "docs: add refactoring baseline metrics"
```

---

### Task 0.3: Create Metrics Script

**Files:**
- Create: `scripts/refactor_metrics.sh`

**Step 1: Write the script**
```bash
#!/usr/bin/env bash
# Refactoring validation metrics script
# Usage: ./scripts/refactor_metrics.sh

set -e
echo "=== PDFTranslator Refactoring Metrics ==="
echo ""

echo "--- Tests ---"
python -m pytest tests/ --tb=short -q "$@" 2>&1 | tail -5
echo ""

echo "--- Coverage ---"
python -m pytest tests/ --cov=src/pdftranslator --cov-report=term-missing --tb=short -q "$@" 2>&1 | tail -10 || echo "Coverage not available"
echo ""

echo "--- Lint ---"
python -m ruff check src/ 2>&1 | tail -5 || echo "Ruff not available"
echo ""

echo "--- Import Check ---"
python -c "import pdftranslator; print('Import OK')" 2>&1 || echo "Import FAILED"
echo ""

echo "--- Circular Import Check ---"
python -c "
from pdftranslator.core.config.settings import Settings
from pdftranslator.database.connection import DatabasePool
from pdftranslator.infrastructure.llm.factory import LLMFactory
from pdftranslator.services.translator import TranslatorService
print('No circular imports detected')
" 2>&1 || echo "Circular import DETECTED"
```

**Step 2: Make executable**
```bash
chmod +x scripts/refactor_metrics.sh
```

**Step 3: Test the script**
```bash
./scripts/refactor_metrics.sh
```
Expected: All sections output something (tests may have failures for integration tests, that's OK for baseline).

**Step 4: Commit**
```bash
git add scripts/refactor_metrics.sh
git commit -m "tool: add refactoring metrics validation script"
```

---

### Task 0.4: Merge Phase 0 and Create Phase 1 Branch

**Step 1: Verify all Phase 0 tasks complete**
```bash
git tag -l "refactor-safe-point"
ls docs/plans/refactor-baseline.md
ls scripts/refactor_metrics.sh
```

**Step 2: Merge Phase 0 to main**
```bash
git checkout main
git merge refactor/solid-phase-0 --no-ff -m "refactor: Phase 0 - safety tag, baseline, metrics script"
```

**Step 3: Create Phase 1 branch**
```bash
git checkout -b refactor/solid-phase-1
```

---

## Phase 1: Domain Layer — Models and Protocols

### Task 1.1: Create domain/models/ Package

**Files:**
- Create: `src/pdftranslator/domain/__init__.py`
- Create: `src/pdftranslator/domain/models/__init__.py`
- Create: `src/pdftranslator/domain/models/work.py`
- Create: `src/pdftranslator/domain/models/glossary.py`
- Create: `src/pdftranslator/domain/models/entity.py`
- Create: `src/pdftranslator/domain/models/file.py`
- Create: `src/pdftranslator/domain/models/substitution.py`

**Step 1: Write failing test for domain models import**
```python
# tests/domain/models/test_work_model.py
"""Tests for domain work models."""
from pdftranslator.domain.models.work import Work, Volume, Chapter


def test_work_dataclass_exists():
    work = Work(id=1, title="Test Book")
    assert work.title == "Test Book"
    assert work.id == 1


def test_volume_dataclass_exists():
    volume = Volume(id=1, work_id=1, volume_number=1)
    assert volume.volume_number == 1
    assert volume.glossary_build_status == "pending"


def test_chapter_dataclass_nullable_number():
    chapter = Chapter(id=1, volume_id=1, chapter_number=None, title="Prologue")
    assert chapter.chapter_number is None


def test_chapter_dataclass_numbered():
    chapter = Chapter(id=1, volume_id=1, chapter_number=5, title="Chapter 5")
    assert chapter.chapter_number == 5
```

**Step 2: Run test to verify it fails**
```bash
pytest tests/domain/models/test_work_model.py -v
```
Expected: FAIL — `ModuleNotFoundError: No module named 'pdftranslator.domain'`

**Step 3: Create domain package structure**
```bash
mkdir -p src/pdftranslator/domain/models
```

**Step 4: Write `src/pdftranslator/domain/__init__.py`**
```python
"""Domain layer — pure business models, protocols, and services."""
```

**Step 5: Write `src/pdftranslator/domain/models/__init__.py`**
```python
"""Domain models — source of truth for all entities."""
from pdftranslator.domain.models.work import Work, Volume, Chapter
from pdftranslator.domain.models.glossary import GlossaryEntry, TermContext, ContextExample
from pdftranslator.domain.models.entity import (
    EntityCandidate,
    BuildResult,
    GlossaryBuildProgress,
    EntityBlacklist,
    FantasyTerm,
)
from pdftranslator.domain.models.file import UploadedFile
from pdftranslator.domain.models.substitution import SubstitutionRule

__all__ = [
    "Work", "Volume", "Chapter",
    "GlossaryEntry", "TermContext", "ContextExample",
    "EntityCandidate", "BuildResult", "GlossaryBuildProgress",
    "EntityBlacklist", "FantasyTerm",
    "UploadedFile",
    "SubstitutionRule",
]
```

**Step 6: Write `src/pdftranslator/domain/models/work.py`**

Copy from `src/pdftranslator/core/models/work.py` with these changes:
- Remove `Optional` import from `typing`, use `X | None`
- Remove `List` import from `typing`, use `list[X]`
- Ensure ALL SQL columns are represented (see design doc MOD-1)

```python
"""Domain models for works, volumes, and chapters.

Maps directly from SQL schema:
- works → Work
- volumes → Volume
- chapters → Chapter
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Work:
    id: int | None = None
    title: str = ""
    title_translated: str | None = None
    source_lang: str | None = None
    target_lang: str | None = None
    author: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


@dataclass
class Volume:
    id: int | None = None
    work_id: int | None = None
    volume_number: int = 0
    title: str | None = None
    full_text: str | None = None
    translated_text: str | None = None
    embedding: list[float] | None = None
    glossary_built_at: datetime | None = None
    created_at: datetime | None = None
    glossary_build_status: str = "pending"
    glossary_error_message: str | None = None
    glossary_resume_phase: str | None = None


@dataclass
class Chapter:
    id: int | None = None
    volume_id: int | None = None
    chapter_number: int | None = None
    title: str | None = None
    start_position: int | None = None
    end_position: int | None = None
    original_text: str | None = None
    translated_text: str | None = None
    embedding: list[float] | None = None
    created_at: datetime | None = None
```

**Step 7: Write `src/pdftranslator/domain/models/glossary.py`**

IMPORTANT: This is the unified version that resolves DUP-2 and DUP-3. Includes all SQL columns (MOD-1 fix).

```python
"""Domain models for glossary entries, contexts, and examples.

Maps directly from SQL schema:
- glossary_terms → GlossaryEntry
- term_contexts → TermContext
- context_examples → ContextExample
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class GlossaryEntry:
    id: int | None = None
    work_id: int | None = None
    term: str = ""
    translation: str | None = None
    notes: str | None = None
    is_proper_noun: bool = False
    entity_type: str = "other"
    do_not_translate: bool = False
    is_verified: bool = False
    confidence: float = 0.0
    context: str | None = None
    frequency: int = 0
    source_lang: str = "en"
    target_lang: str = "es"
    embedding: list[float] | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


@dataclass
class TermContext:
    id: int | None = None
    term_id: int | None = None
    context_hint: str = ""
    translation: str = ""
    example_usage: str | None = None
    examples: list[ContextExample] = field(default_factory=list)
    created_at: datetime | None = None


@dataclass
class ContextExample:
    id: int | None = None
    context_id: int | None = None
    original_sentence: str = ""
    translated_sentence: str = ""
    chapter_id: int | None = None
    created_at: datetime | None = None
```

**Step 8: Write `src/pdftranslator/domain/models/entity.py`**
```python
"""Domain models for entity extraction and glossary building.

Maps from SQL schema:
- glossary_build_progress → GlossaryBuildProgress
- entity_blacklist → EntityBlacklist
- fantasy_terms → FantasyTerm
EntityCandidate and BuildResult are pipeline-only (no SQL table).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class EntityCandidate:
    text: str = ""
    entity_type: str = "other"
    frequency: int = 1
    contexts: list[str] = field(default_factory=list)
    confidence: float = 0.0
    source_language: str = "en"
    translation: str | None = None
    validated: bool = False

    def add_context(self, context: str) -> None:
        if context and context not in self.contexts:
            self.contexts.append(context)

    def best_context(self) -> str:
        return self.contexts[0] if self.contexts else ""

    def to_embed_text(self) -> str:
        return f"{self.text} {self.entity_type} {self.best_context()}"


@dataclass
class BuildResult:
    extracted: int = 0
    new: int = 0
    skipped: int = 0
    entities_by_type: dict[str, int] = field(default_factory=dict)


@dataclass
class GlossaryBuildProgress:
    id: int | None = None
    work_id: int | None = None
    volume_id: int | None = None
    entity_text: str = ""
    phase: str = "extracted"
    entity_type: str | None = None
    frequency: int = 1
    contexts: list[str] = field(default_factory=list)
    translation: str | None = None
    embedding: list[float] | None = None
    validation_batch: int | None = None
    translation_batch: int | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    def is_complete(self) -> bool:
        return self.phase == "saved"

    def next_phase(self) -> str:
        phases = ["extracted", "validated", "translated", "saved"]
        current = phases.index(self.phase) if self.phase in phases else 0
        return phases[min(current + 1, len(phases) - 1)]


@dataclass
class EntityBlacklist:
    id: int | None = None
    term: str = ""
    reason: str | None = None


@dataclass
class FantasyTerm:
    id: int | None = None
    term: str = ""
    entity_type: str = "other"
    do_not_translate: bool = False
    context_hint: str | None = None
```

**Step 9: Write `src/pdftranslator/domain/models/file.py`**
```python
"""Domain model for uploaded files.

Maps from SQL schema: uploaded_files → UploadedFile
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass
class UploadedFile:
    id: int | None = None
    filename: str = ""
    original_name: str = ""
    file_path: str | None = None
    file_size: int = 0
    file_type: str = ""
    mime_type: str | None = None
    work_id: int | None = None
    volume_id: int | None = None
    status: str = "uploaded"
    error_message: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
```

**Step 10: Write `src/pdftranslator/domain/models/substitution.py`**
```python
"""Domain model for text substitution rules.

Maps from SQL schema: text_substitution_rules → SubstitutionRule
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass
class SubstitutionRule:
    id: int | None = None
    name: str = ""
    pattern: str = ""
    replacement: str = ""
    description: str | None = None
    is_active: bool = True
    apply_on_extract: bool = True
    created_at: datetime | None = None
    updated_at: datetime | None = None
```

**Step 11: Run tests**
```bash
pytest tests/domain/models/test_work_model.py -v
```
Expected: PASS

**Step 12: Write additional model tests**
```python
# tests/domain/models/test_glossary_model.py
"""Tests for domain glossary models."""
from pdftranslator.domain.models.glossary import GlossaryEntry, TermContext, ContextExample


def test_glossary_entry_has_new_sql_columns():
    entry = GlossaryEntry(
        id=1, work_id=1, term="Dragon",
        notes="Important entity", do_not_translate=True,
        is_verified=True, confidence=0.95,
    )
    assert entry.notes == "Important entity"
    assert entry.do_not_translate is True
    assert entry.is_verified is True
    assert entry.confidence == 0.95


def test_term_context_has_examples_field():
    example = ContextExample(original_sentence="The dragon flew.", translated_sentence="El dragón voló.")
    ctx = TermContext(context_hint="Mythical creature", translation="dragón", examples=[example])
    assert len(ctx.examples) == 1


# tests/domain/models/test_entity_model.py
"""Tests for domain entity models."""
from pdftranslator.domain.models.entity import EntityCandidate, BuildResult, GlossaryBuildProgress


def test_entity_candidate_add_context():
    e = EntityCandidate(text="Dragon")
    e.add_context("The dragon flew over the mountains.")
    e.add_context("The dragon flew over the mountains.")  # Duplicate
    assert len(e.contexts) == 1


def test_entity_candidate_best_context():
    e = EntityCandidate(text="Dragon", contexts=["ctx1", "ctx2"])
    assert e.best_context() == "ctx1"


def test_glossary_build_progress_next_phase():
    p = GlossaryBuildProgress(phase="extracted")
    assert p.next_phase() == "validated"
    assert p.is_complete() is False


def test_glossary_build_progress_is_complete():
    p = GlossaryBuildProgress(phase="saved")
    assert p.is_complete() is True
```

**Step 13: Run all new model tests**
```bash
pytest tests/domain/ -v
```
Expected: ALL PASS

**Step 14: Commit**
```bash
git add src/pdftranslator/domain/ tests/domain/
git commit -m "feat(domain): create domain models layer with full SQL schema mapping"
```

---

### Task 1.2: Create Backward-Compatible Re-exports

**Files:**
- Modify: `src/pdftranslator/core/models/__init__.py`
- Modify: `src/pdftranslator/core/models/work.py`
- Modify: `src/pdftranslator/database/models.py`

**Step 1: Write failing test for backward compatibility**
```python
# tests/domain/test_backward_compat.py
"""Tests that old import paths still work after domain migration."""


def test_core_models_work_import():
    from pdftranslator.core.models.work import Work, Volume, Chapter
    w = Work(id=1, title="Test")
    assert w.title == "Test"


def test_database_models_import():
    from pdftranslator.database.models import Work, Volume, Chapter, GlossaryEntry
    from pdftranslator.database.models import UploadedFile, SubstitutionRule
    from pdftranslator.database.models import EntityCandidate, BuildResult
    assert True


def test_glossary_entry_has_new_fields():
    from pdftranslator.database.models import GlossaryEntry
    entry = GlossaryEntry(notes="test", do_not_translate=True, is_verified=True, confidence=0.9)
    assert entry.notes == "test"
    assert entry.do_not_translate is True
```

**Step 2: Run test to verify it fails (GlossaryEntry doesn't have new fields yet)**
```bash
pytest tests/domain/test_backward_compat.py -v
```
Expected: FAIL on `test_glossary_entry_has_new_fields`

**Step 3: Update `core/models/work.py` to re-export from domain**
```python
"""Work models — re-exported from domain for backward compatibility.

DEPRECATED: Import from pdftranslator.domain.models.work instead.
"""
from pdftranslator.domain.models.work import Work, Volume, Chapter  # noqa: F401

__all__ = ["Work", "Volume", "Chapter"]
```

**Step 4: Update `core/models/__init__.py` to re-export from domain**
```python
"""Core models — re-exported from domain for backward compatibility.

DEPRECATED: Import from pdftranslator.domain.models instead.
"""
from pdftranslator.domain.models.work import Work, Volume, Chapter  # noqa: F401
from pdftranslator.domain.models.glossary import GlossaryEntry, TermContext, ContextExample  # noqa: F401

__all__ = ["Work", "Volume", "Chapter", "GlossaryEntry", "TermContext", "ContextExample"]
```

**Step 5: Update `database/models.py` to re-export from domain**
```python
"""Database models — re-exported from domain for backward compatibility.

DEPRECATED: Import from pdftranslator.domain.models instead.
"""
from pdftranslator.domain.models.work import Work, Volume, Chapter  # noqa: F401
from pdftranslator.domain.models.glossary import GlossaryEntry, TermContext, ContextExample  # noqa: F401
from pdftranslator.domain.models.entity import (  # noqa: F401
    EntityCandidate,
    BuildResult,
    GlossaryBuildProgress,
    EntityBlacklist,
    FantasyTerm,
)
from pdftranslator.domain.models.file import UploadedFile  # noqa: F401
from pdftranslator.domain.models.substitution import SubstitutionRule  # noqa: F401

__all__ = [
    "Work", "Volume", "Chapter",
    "GlossaryEntry", "TermContext", "ContextExample",
    "EntityCandidate", "BuildResult", "GlossaryBuildProgress",
    "EntityBlacklist", "FantasyTerm",
    "UploadedFile",
    "SubstitutionRule",
]
```

**Step 6: Run backward compat tests**
```bash
pytest tests/domain/test_backward_compat.py -v
```
Expected: ALL PASS

**Step 7: Run ALL existing tests to verify nothing broke**
```bash
pytest tests/ --tb=short -q
```
Expected: Same results as baseline (no new failures)

**Step 8: Commit**
```bash
git add src/pdftranslator/core/models/ src/pdftranslator/database/models.py tests/domain/
git commit -m "refactor: re-export models from domain layer for backward compatibility"
```

---

### Task 1.3: Create Domain Exceptions

**Files:**
- Create: `src/pdftranslator/domain/exceptions/__init__.py`
- Create: `src/pdftranslator/domain/exceptions/errors.py`
- Modify: `src/pdftranslator/database/exceptions.py`
- Modify: `src/pdftranslator/core/exceptions/__init__.py`

**Step 1: Write failing test**
```python
# tests/domain/exceptions/test_errors.py
"""Tests for domain exceptions."""
from pdftranslator.domain.exceptions.errors import (
    DomainError,
    DBConnectionError,
    QueryError,
    EntityNotFoundError,
    DuplicateEntityError,
)


def test_domain_error_is_base():
    assert issubclass(DBConnectionError, DomainError)
    assert issubclass(QueryError, DomainError)
    assert issubclass(EntityNotFoundError, DomainError)
    assert issubclass(DuplicateEntityError, DomainError)


def test_db_connection_error_does_not_shadow_builtin():
    import builtins
    assert "DBConnectionError" not in dir(builtins)
    assert "ConnectionError" in dir(builtins)


def test_backward_compat_database_imports():
    from pdftranslator.database.exceptions import (
        DatabaseError,
        ConnectionError,
        QueryError,
        EntityNotFoundError,
        DuplicateEntityError,
    )
    assert issubclass(ConnectionError, DatabaseError)


def test_backward_compat_core_imports():
    from pdftranslator.core.exceptions import (
        DatabaseError,
        ConnectionError,
        QueryError,
        EntityNotFoundError,
        DuplicateEntityError,
    )
    assert issubclass(ConnectionError, DatabaseError)
```

**Step 2: Run test to verify it fails**
```bash
pytest tests/domain/exceptions/ -v
```
Expected: FAIL — `ModuleNotFoundError: No module named 'pdftranslator.domain.exceptions'`

**Step 3: Create domain exceptions package**
```bash
mkdir -p src/pdftranslator/domain/exceptions
```

**Step 4: Write `src/pdftranslator/domain/exceptions/errors.py`**
```python
"""Domain exceptions — no dependencies on infrastructure.

Resolves DIP-5: core should not depend on database.
Resolves SHD-1: DBConnectionError does not shadow builtin ConnectionError.
"""


class DomainError(Exception):
    """Base exception for all domain errors."""


class DBConnectionError(DomainError):
    """Database connection error."""


class QueryError(DomainError):
    """SQL query error."""


class EntityNotFoundError(DomainError):
    """Entity not found in data store."""


class DuplicateEntityError(DomainError):
    """Entity already exists in data store."""
```

**Step 5: Write `src/pdftranslator/domain/exceptions/__init__.py`**
```python
"""Domain exceptions package."""
from pdftranslator.domain.exceptions.errors import (  # noqa: F401
    DomainError,
    DBConnectionError,
    QueryError,
    EntityNotFoundError,
    DuplicateEntityError,
)

__all__ = [
    "DomainError",
    "DBConnectionError",
    "QueryError",
    "EntityNotFoundError",
    "DuplicateEntityError",
]
```

**Step 6: Update `database/exceptions.py` to re-export from domain**
```python
"""Database exceptions — re-exported from domain for backward compatibility.

DEPRECATED: Import from pdftranslator.domain.exceptions instead.

NOTE: ConnectionError is kept as alias for DBConnectionError
to maintain backward compatibility, but prefer DBConnectionError
to avoid shadowing the Python builtin.
"""
from pdftranslator.domain.exceptions.errors import (  # noqa: F401
    DomainError as DatabaseError,
    DBConnectionError as ConnectionError,
    QueryError,
    EntityNotFoundError,
    DuplicateEntityError,
)

__all__ = [
    "DatabaseError",
    "ConnectionError",
    "QueryError",
    "EntityNotFoundError",
    "DuplicateEntityError",
]
```

**Step 7: Update `core/exceptions/__init__.py` to re-export from domain**
```python
"""Core exceptions — re-exported from domain for backward compatibility.

DEPRECATED: Import from pdftranslator.domain.exceptions instead.
"""
from pdftranslator.domain.exceptions.errors import (  # noqa: F401
    DomainError as DatabaseError,
    DBConnectionError as ConnectionError,
    QueryError,
    EntityNotFoundError,
    DuplicateEntityError,
)

__all__ = [
    "DatabaseError",
    "ConnectionError",
    "QueryError",
    "EntityNotFoundError",
    "DuplicateEntityError",
]
```

**Step 8: Run tests**
```bash
pytest tests/domain/exceptions/ tests/database/test_exceptions.py -v
```
Expected: ALL PASS

**Step 9: Run all existing tests**
```bash
pytest tests/ --tb=short -q
```
Expected: No new failures

**Step 10: Commit**
```bash
git add src/pdftranslator/domain/exceptions/ src/pdftranslator/database/exceptions.py src/pdftranslator/core/exceptions/ tests/domain/
git commit -m "feat(domain): create domain exceptions, fix ConnectionError shadowing builtin"
```

---

### Task 1.4: Create Domain Protocols — LLM Interfaces (ISP)

**Files:**
- Create: `src/pdftranslator/domain/protocols/__init__.py`
- Create: `src/pdftranslator/domain/protocols/llm.py`

**Step 1: Write failing test**
```python
# tests/domain/protocols/test_llm_protocol.py
"""Tests for LLM protocol segregation (ISP-1)."""
from pdftranslator.domain.protocols.llm import (
    TextGenerator,
    TokenCounter,
    TextSplitter,
    LLMClient,
)
from pdftranslator.infrastructure.llm.nvidia import NvidiaLLM
from pdftranslator.infrastructure.llm.gemini import GeminiLLM
from pdftranslator.infrastructure.llm.ollama import OllamaLLM
from pdftranslator.core.config.settings import Settings


def test_text_generator_protocol():
    class MockGenerator:
        def generate(self, prompt: str) -> str:
            return "response"
    gen = MockGenerator()
    assert isinstance(gen, TextGenerator)


def test_nvidia_llm_satisfies_llm_client():
    settings = Settings()
    client = NvidiaLLM(settings)
    assert isinstance(client, LLMClient)


def test_gemini_llm_satisfies_llm_client():
    settings = Settings()
    client = GeminiLLM(settings)
    assert isinstance(client, LLMClient)


def test_ollama_llm_satisfies_llm_client():
    settings = Settings()
    client = OllamaLLM(settings)
    assert isinstance(client, LLMClient)
```

**Step 2: Run test to verify it fails**
```bash
pytest tests/domain/protocols/test_llm_protocol.py -v
```
Expected: FAIL — `ModuleNotFoundError: No module named 'pdftranslator.domain.protocols'`

**Step 3: Create protocols package**
```bash
mkdir -p src/pdftranslator/domain/protocols
```

**Step 4: Write `src/pdftranslator/domain/protocols/llm.py`**

This segregates the monolithic `LLMClient` into 3 focused interfaces (ISP-1 fix).

```python
"""LLM protocol definitions — segregated interfaces.

Resolves ISP-1: Consumers that only need text generation
should not be forced to depend on token counting or splitting.
"""
from __future__ import annotations

from typing import Protocol, runtime_checkable

from pdftranslator.core.config.llm import BCP47Language


@runtime_checkable
class TextGenerator(Protocol):
    """Minimal interface for text generation."""

    def call_model(self, prompt: str) -> str:
        """Generate text from a prompt."""
        ...


@runtime_checkable
class TokenCounter(Protocol):
    """Interface for token counting."""

    def count_tokens(self, text: str) -> int:
        """Count tokens in text."""
        ...


@runtime_checkable
class TextSplitter(Protocol):
    """Interface for text splitting within token limits."""

    def split_into_limit(
        self, text: str, language: BCP47Language = BCP47Language.ENGLISH
    ) -> list[str]:
        """Split text into chunks within token limits."""
        ...


@runtime_checkable
class LLMClient(TextGenerator, TokenCounter, TextSplitter, Protocol):
    """Full LLM client — composed of segregated interfaces.

    For consumers that need all three capabilities.
    Prefer the specific interface when you don't need everything.
    """

    def get_current_model_name(self) -> str:
        """Get the name of the currently active model."""
        ...
```

**Step 5: Write `src/pdftranslator/domain/protocols/__init__.py`**
```python
"""Domain protocols — interfaces that infrastructure must implement."""
from pdftranslator.domain.protocols.llm import (  # noqa: F401
    TextGenerator,
    TokenCounter,
    TextSplitter,
    LLMClient,
)

__all__ = ["TextGenerator", "TokenCounter", "TextSplitter", "LLMClient"]
```

**Step 6: Run protocol compliance tests**
```bash
pytest tests/domain/protocols/test_llm_protocol.py -v
```
Expected: PASS (NvidiaLLM, GeminiLLM, OllamaLLM already implement these methods)

**Step 7: Run all tests**
```bash
pytest tests/ --tb=short -q
```
Expected: No new failures

**Step 8: Commit**
```bash
git add src/pdftranslator/domain/protocols/ tests/domain/protocols/
git commit -m "feat(domain): create segregated LLM protocols (ISP-1 fix)"
```

---

### Task 1.5: Create Domain Protocols — Embedding, Reranking, Audio, Document Parser

**Files:**
- Create: `src/pdftranslator/domain/protocols/embedding.py`
- Create: `src/pdftranslator/domain/protocols/reranking.py`
- Create: `src/pdftranslator/domain/protocols/audio_synthesizer.py`
- Create: `src/pdftranslator/domain/protocols/document_parser.py`
- Create: `src/pdftranslator/domain/protocols/repositories.py`
- Modify: `src/pdftranslator/domain/protocols/__init__.py`

**Step 1: Write protocol compliance tests**
```python
# tests/domain/protocols/test_protocols.py
"""Tests for all domain protocols."""
from pdftranslator.domain.protocols.embedding import EmbeddingProvider
from pdftranslator.domain.protocols.reranking import RerankingProvider
from pdftranslator.domain.protocols.audio_synthesizer import AudioSynthesizer
from pdftranslator.domain.protocols.document_parser import DocumentParser
from pdftranslator.domain.protocols.repositories import (
    ReadRepository,
    WriteRepository,
    GlossaryProgressTracker,
)


def test_embedding_provider_protocol():
    class MockEmbedder:
        def embed_query(self, text: str) -> list[float]:
            return [0.1, 0.2]
        def embed_documents(self, texts: list[str]) -> list[list[float]]:
            return [[0.1, 0.2]]
    assert isinstance(MockEmbedder(), EmbeddingProvider)


def test_reranking_provider_protocol():
    class MockReranker:
        def rerank(self, query: str, documents: list, top_n: int = 5) -> list:
            return documents[:top_n]
    assert isinstance(MockReranker(), RerankingProvider)


def test_audio_synthesizer_protocol():
    class MockSynth:
        @property
        def is_available(self) -> bool:
            return True
        @property
        def name(self) -> str:
            return "mock"
        def synthesize(self, text: str, output_path, voice: str = "default", speed: float = 1.0, language: str = "es") -> bool:
            return True
        def merge_audio(self, audio_files: list, output_path) -> bool:
            return True
    assert isinstance(MockSynth(), AudioSynthesizer)


def test_document_parser_protocol():
    class MockParser:
        @property
        def supported_extensions(self) -> set[str]:
            return {".pdf", ".epub"}
        def parse(self, file_path: str) -> str:
            return "extracted text"
    assert isinstance(MockParser(), DocumentParser)


def test_glossary_progress_tracker_protocol():
    class MockTracker:
        def save_extracted(self, work_id, volume_id, entities): return []
        def get_pending_for_phase(self, work_id, volume_id, phase): return []
        def batch_update_phase(self, ids, phase, batch_num=None): pass
        def get_resume_point(self, work_id, volume_id): return ("extracted", None)
        def cleanup_completed(self, volume_id): pass
    assert isinstance(MockTracker(), GlossaryProgressTracker)
```

**Step 2: Run test to verify it fails**
```bash
pytest tests/domain/protocols/test_protocols.py -v
```
Expected: FAIL — missing modules

**Step 3: Write all protocol files**

`src/pdftranslator/domain/protocols/embedding.py`:
```python
"""Embedding provider protocol.

Resolves OCP-3 and ISP-3: Embedding logic should be swappable
and consumers should only depend on what they need.
"""
from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class EmbeddingProvider(Protocol):
    """Interface for text embedding services."""

    def embed_query(self, text: str) -> list[float]:
        """Generate embedding for a single text."""
        ...

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for multiple texts."""
        ...
```

`src/pdftranslator/domain/protocols/reranking.py`:
```python
"""Reranking provider protocol.

Resolves ISP-3: Reranking is a separate concern from embedding.
"""
from __future__ import annotations

from typing import Protocol, runtime_checkable

from langchain_core.documents import Document


@runtime_checkable
class RerankingProvider(Protocol):
    """Interface for document reranking services."""

    def rerank(
        self, query: str, documents: list[Document], top_n: int = 5
    ) -> list[Document]:
        """Rerank documents by relevance to query."""
        ...
```

`src/pdftranslator/domain/protocols/audio_synthesizer.py`:
```python
"""Audio synthesizer protocol.

Resolves OCP-4 and SRP-7: TTS backends should be swappable
without modifying existing code.
"""
from __future__ import annotations

from pathlib import Path
from typing import Protocol, runtime_checkable


@runtime_checkable
class AudioSynthesizer(Protocol):
    """Interface for text-to-speech synthesis."""

    @property
    def is_available(self) -> bool:
        """Check if this engine is available on the current system."""
        ...

    @property
    def name(self) -> str:
        """Engine name for logging and configuration."""
        ...

    def synthesize(
        self,
        text: str,
        output_path: Path,
        voice: str = "default",
        speed: float = 1.0,
        language: str = "es",
    ) -> bool:
        """Synthesize text to audio file. Returns True on success."""
        ...

    def merge_audio(
        self,
        audio_files: list[Path],
        output_path: Path,
    ) -> bool:
        """Merge multiple audio files into one. Returns True on success."""
        ...
```

`src/pdftranslator/domain/protocols/document_parser.py`:
```python
"""Document parser protocol.

Resolves DIP-7: Consumers should not depend on specific
document extraction implementations.
"""
from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class DocumentParser(Protocol):
    """Interface for document text extraction."""

    @property
    def supported_extensions(self) -> set[str]:
        """File extensions this parser supports (e.g., {'.pdf', '.epub'})."""
        ...

    def parse(self, file_path: str) -> str | None:
        """Extract text from a document file.

        Returns None if extraction fails.
        """
        ...
```

`src/pdftranslator/domain/protocols/repositories.py`:
```python
"""Repository protocols — segregated interfaces.

Resolves ISP-2 and LSP-1: Not all repositories need full CRUD.
GlossaryBuildProgressRepository only needs batch operations.
"""
from __future__ import annotations

from typing import Protocol, TypeVar, runtime_checkable

T = TypeVar("T")


@runtime_checkable
class ReadRepository(Protocol[T]):
    """Read-only repository interface."""

    def get_by_id(self, id: int) -> T | None:
        ...

    def get_all(self) -> list[T]:
        ...


@runtime_checkable
class WriteRepository(Protocol[T]):
    """Write-only repository interface."""

    def create(self, entity: T) -> T:
        ...

    def update(self, entity: T) -> T:
        ...

    def delete(self, id: int) -> bool:
        ...


@runtime_checkable
class GlossaryProgressTracker(Protocol):
    """Interface for glossary build progress tracking.

    Resolves LSP-1: GlossaryBuildProgressRepository
    should not be forced to implement full CRUD.
    """

    def save_extracted(
        self, work_id: int, volume_id: int, entities: list
    ) -> list:
        ...

    def get_pending_for_phase(
        self, work_id: int, volume_id: int, phase: str
    ) -> list:
        ...

    def batch_update_phase(
        self,
        ids: list[int],
        phase: str,
        batch_num: int | None = None,
    ) -> None:
        ...

    def get_resume_point(
        self, work_id: int, volume_id: int
    ) -> tuple[str, int | None]:
        ...

    def cleanup_completed(self, volume_id: int) -> None:
        ...
```

**Step 4: Update `__init__.py`**
```python
"""Domain protocols — interfaces that infrastructure must implement."""
from pdftranslator.domain.protocols.llm import (  # noqa: F401
    TextGenerator,
    TokenCounter,
    TextSplitter,
    LLMClient,
)
from pdftranslator.domain.protocols.embedding import EmbeddingProvider  # noqa: F401
from pdftranslator.domain.protocols.reranking import RerankingProvider  # noqa: F401
from pdftranslator.domain.protocols.audio_synthesizer import AudioSynthesizer  # noqa: F401
from pdftranslator.domain.protocols.document_parser import DocumentParser  # noqa: F401
from pdftranslator.domain.protocols.repositories import (  # noqa: F401
    ReadRepository,
    WriteRepository,
    GlossaryProgressTracker,
)

__all__ = [
    "TextGenerator", "TokenCounter", "TextSplitter", "LLMClient",
    "EmbeddingProvider", "RerankingProvider",
    "AudioSynthesizer", "DocumentParser",
    "ReadRepository", "WriteRepository", "GlossaryProgressTracker",
]
```

**Step 5: Run tests**
```bash
pytest tests/domain/protocols/ -v
```
Expected: ALL PASS

**Step 6: Run all tests**
```bash
pytest tests/ --tb=short -q
```
Expected: No new failures

**Step 7: Commit**
```bash
git add src/pdftranslator/domain/protocols/ tests/domain/protocols/
git commit -m "feat(domain): create embedding, reranking, audio, document, and repository protocols"
```

---

### Task 1.6: Move GlossaryPostProcessor to Domain Services

**Files:**
- Create: `src/pdftranslator/domain/services/__init__.py`
- Create: `src/pdftranslator/domain/services/glossary_post_processor.py`
- Modify: `src/pdftranslator/cli/services/glossary_post_processor.py`
- Modify: `src/pdftranslator/services/glossary_translator.py`

**Step 1: Write failing test**
```python
# tests/domain/services/test_glossary_post_processor_compat.py
"""Tests that GlossaryPostProcessor is importable from domain."""
from pdftranslator.domain.services.glossary_post_processor import GlossaryPostProcessor as DomainProcessor
from pdftranslator.cli.services.glossary_post_processor import GlossaryPostProcessor as CliProcessor
from pdftranslator.database.models import GlossaryEntry


def test_domain_processor_same_interface():
    entries = [GlossaryEntry(term="Dragon", translation="dragón")]
    processor = DomainProcessor(entries, "es")
    assert processor is not None


def test_cli_processor_reexports_domain():
    assert CliProcessor is DomainProcessor
```

**Step 2: Create domain services package**
```bash
mkdir -p src/pdftranslator/domain/services
```

**Step 3: Copy GlossaryPostProcessor to domain (change imports to use domain models)**
Copy `cli/services/glossary_post_processor.py` to `domain/services/glossary_post_processor.py`, updating the import:
```python
from pdftranslator.domain.models.glossary import GlossaryEntry
```

**Step 4: Update CLI version to re-export**
```python
# cli/services/glossary_post_processor.py
"""GlossaryPostProcessor — re-exported from domain for backward compatibility.

DEPRECATED: Import from pdftranslator.domain.services.glossary_post_processor instead.
"""
from pdftranslator.domain.services.glossary_post_processor import GlossaryPostProcessor  # noqa: F401

__all__ = ["GlossaryPostProcessor"]
```

**Step 5: Update services/glossary_translator.py import**
Change:
```python
from pdftranslator.cli.services.glossary_post_processor import GlossaryPostProcessor
```
To:
```python
from pdftranslator.domain.services.glossary_post_processor import GlossaryPostProcessor
```

**Step 6: Run tests**
```bash
pytest tests/domain/services/ tests/cli/test_glossary_post_processor.py -v
```
Expected: ALL PASS

**Step 7: Run all tests**
```bash
pytest tests/ --tb=short -q
```
Expected: No new failures

**Step 8: Commit**
```bash
git add src/pdftranslator/domain/services/ src/pdftranslator/cli/services/ src/pdftranslator/services/ tests/domain/services/
git commit -m "refactor(domain): move GlossaryPostProcessor to domain services (DIP-6 fix)"
```

---

### Task 1.7: Merge Phase 1 and Run Full Validation

**Step 1: Run full metrics**
```bash
./scripts/refactor_metrics.sh
```
Expected: Tests pass, no import errors, no circular imports

**Step 2: Run all tests**
```bash
pytest tests/ --tb=short -q
```
Expected: Same or better than baseline

**Step 3: Merge Phase 1 to main**
```bash
git checkout main
git merge refactor/solid-phase-1 --no-ff -m "refactor: Phase 1 - domain layer with models, protocols, exceptions"
```

**Step 4: Create Phase 2 branch**
```bash
git checkout -b refactor/solid-phase-2
```

---

## Phase 2: Infrastructure Layer — Implement Protocols

### Task 2.1: Create NvidiaEmbeddingProvider

**Files:**
- Create: `src/pdftranslator/infrastructure/embedding/__init__.py`
- Create: `src/pdftranslator/infrastructure/embedding/nvidia_embedding.py`

**Step 1: Write failing test**
```python
# tests/infrastructure/embedding/test_nvidia_embedding.py
"""Tests for NvidiaEmbeddingProvider protocol compliance."""
from pdftranslator.domain.protocols.embedding import EmbeddingProvider
from pdftranslator.infrastructure.embedding.nvidia_embedding import NvidiaEmbeddingProvider


def test_nvidia_embedding_satisfies_protocol():
    provider = NvidiaEmbeddingProvider()
    assert isinstance(provider, EmbeddingProvider)
```

**Step 2: Run test to verify it fails**
```bash
pytest tests/infrastructure/embedding/ -v
```
Expected: FAIL

**Step 3: Create infrastructure/embedding package**
```bash
mkdir -p src/pdftranslator/infrastructure/embedding
```

**Step 4: Write `src/pdftranslator/infrastructure/embedding/nvidia_embedding.py`**
```python
"""NVIDIA embedding provider — implements EmbeddingProvider protocol.

Resolves DIP-2: Embedding logic decoupled from VectorStoreService.
"""
from __future__ import annotations

from typing import Optional

from langchain_nvidia_ai_endpoints import NVIDIAEmbeddings
from pdftranslator.core.config.settings import Settings
from pdftranslator.domain.protocols.embedding import EmbeddingProvider


class NvidiaEmbeddingProvider:
    """NVIDIA NIM-based embedding provider."""

    def __init__(self, settings: Settings | None = None):
        self._settings = settings or Settings.get()
        self._embedder: Optional[NVIDIAEmbeddings] = None

    @property
    def embedder(self) -> NVIDIAEmbeddings:
        if self._embedder is None:
            nvidia_config = self._settings.llm.nvidia
            self._embedder = NVIDIAEmbeddings(
                model=nvidia_config.embed_model,
                api_key=self._settings.llm.nvidia_api_key,
            )
        return self._embedder

    def embed_query(self, text: str) -> list[float]:
        return self.embedder.embed_query(text)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return self.embedder.embed_documents(texts)
```

**Step 5: Write `__init__.py`**
```python
"""Embedding provider implementations."""
from pdftranslator.infrastructure.embedding.nvidia_embedding import NvidiaEmbeddingProvider  # noqa: F401

__all__ = ["NvidiaEmbeddingProvider"]
```

**Step 6: Run test**
```bash
pytest tests/infrastructure/embedding/ -v
```
Expected: PASS

**Step 7: Commit**
```bash
git add src/pdftranslator/infrastructure/embedding/ tests/infrastructure/embedding/
git commit -m "feat(infrastructure): create NvidiaEmbeddingProvider implementing EmbeddingProvider"
```

---

### Task 2.2: Create NvidiaRerankingProvider

**Files:**
- Create: `src/pdftranslator/infrastructure/embedding/nvidia_reranking.py`
- Modify: `src/pdftranslator/infrastructure/embedding/__init__.py`

**Step 1: Write failing test**
```python
# tests/infrastructure/embedding/test_nvidia_reranking.py
from pdftranslator.domain.protocols.reranking import RerankingProvider
from pdftranslator.infrastructure.embedding.nvidia_reranking import NvidiaRerankingProvider


def test_nvidia_reranking_satisfies_protocol():
    provider = NvidiaRerankingProvider()
    assert isinstance(provider, RerankingProvider)
```

**Step 2: Write `nvidia_reranking.py`**
```python
"""NVIDIA reranking provider — implements RerankingProvider protocol."""
from __future__ import annotations

from typing import Optional

from langchain_core.documents import Document
from langchain_nvidia_ai_endpoints import NVIDIARerank
from pdftranslator.core.config.settings import Settings
from pdftranslator.domain.protocols.reranking import RerankingProvider


class NvidiaRerankingProvider:
    """NVIDIA NIM-based reranking provider."""

    def __init__(self, settings: Settings | None = None):
        self._settings = settings or Settings.get()
        self._reranker: Optional[NVIDIARerank] = None

    @property
    def reranker(self) -> NVIDIARerank:
        if self._reranker is None:
            nvidia = self._settings.llm.nvidia
            self._reranker = NVIDIARerank(
                model=nvidia.rerank_model,
                api_key=self._settings.llm.nvidia_api_key,
                top_n=nvidia.rerank_top_n,
            )
        return self._reranker

    def rerank(
        self, query: str, documents: list[Document], top_n: int = 5
    ) -> list[Document]:
        if not documents:
            return []
        reranker = NVIDIARerank(
            model=self._settings.llm.nvidia.rerank_model,
            api_key=self._settings.llm.nvidia_api_key,
            top_n=top_n,
        )
        return reranker.compress_documents(documents=documents, query=query)
```

**Step 3: Update `__init__.py`**
```python
from pdftranslator.infrastructure.embedding.nvidia_embedding import NvidiaEmbeddingProvider  # noqa: F401
from pdftranslator.infrastructure.embedding.nvidia_reranking import NvidiaRerankingProvider  # noqa: F401

__all__ = ["NvidiaEmbeddingProvider", "NvidiaRerankingProvider"]
```

**Step 4: Run test and commit**
```bash
pytest tests/infrastructure/embedding/ -v
git add src/pdftranslator/infrastructure/embedding/ tests/infrastructure/embedding/
git commit -m "feat(infrastructure): create NvidiaRerankingProvider implementing RerankingProvider"
```

---

### Task 2.3: Refactor VectorStoreService to Use Injected Providers

**Files:**
- Modify: `src/pdftranslator/database/services/vector_store.py`

**Step 1: Write failing test**
```python
# tests/database/test_vector_store_di.py
"""Tests that VectorStoreService accepts injected providers."""
from unittest.mock import MagicMock
from pdftranslator.domain.protocols.embedding import EmbeddingProvider
from pdftranslator.database.services.vector_store import VectorStoreService


def test_vector_store_accepts_injected_embedder():
    mock_embedder = MagicMock(spec=EmbeddingProvider)
    mock_embedder.embed_query.return_value = [0.1, 0.2, 0.3]
    mock_embedder.embed_documents.return_value = [[0.1, 0.2, 0.3]]
    service = VectorStoreService(embedder=mock_embedder)
    result = service.embed_query("test")
    assert result == [0.1, 0.2, 0.3]
```

**Step 2: Modify `vector_store.py` — add optional DI parameters**
Keep the existing API working (backward compat), add optional `embedder` and `reranker` params:

```python
class VectorStoreService:
    def __init__(
        self,
        embedder: EmbeddingProvider | None = None,
        reranker: RerankingProvider | None = None,
    ):
        self._injected_embedder = embedder
        self._injected_reranker = reranker
        self._config = Settings.get()
        self._embedder: Optional[NVIDIAEmbeddings] = None
        self._reranker: Optional[NVIDIARerank] = None

    @property
    def embedder(self) -> NVIDIAEmbeddings | EmbeddingProvider:
        if self._injected_embedder is not None:
            return self._injected_embedder
        # Legacy path
        if self._embedder is None:
            self._embedder = NVIDIAEmbeddings(...)
        return self._embedder

    # Similar pattern for reranker...
```

**Step 3: Run all tests**
```bash
pytest tests/ --tb=short -q
```

**Step 4: Commit**
```bash
git add src/pdftranslator/database/services/vector_store.py tests/database/test_vector_store_di.py
git commit -m "refactor: VectorStoreService accepts injected EmbeddingProvider/RerankingProvider (DIP-2 partial)"
```

---

### Task 2.4: Create MacSaySynthesizer (AudioSynthesizer Protocol)

**Files:**
- Create: `src/pdftranslator/infrastructure/audio/__init__.py`
- Create: `src/pdftranslator/infrastructure/audio/mac_say_synthesizer.py`
- Create: `src/pdftranslator/infrastructure/audio/ffmpeg_merger.py`

**Step 1: Write failing test**
```python
# tests/infrastructure/audio/test_mac_say_synthesizer.py
from pdftranslator.domain.protocols.audio_synthesizer import AudioSynthesizer
from pdftranslator.infrastructure.audio.mac_say_synthesizer import MacSaySynthesizer


def test_mac_say_satisfies_protocol():
    synth = MacSaySynthesizer.__new__(MacSaySynthesizer)
    assert isinstance(synth, AudioSynthesizer)


def test_mac_say_name():
    synth = MacSaySynthesizer.__new__(MacSaySynthesizer)
    assert synth.name == "mac_say"
```

**Step 2: Create infrastructure/audio package**
```bash
mkdir -p src/pdftranslator/infrastructure/audio
```

**Step 3: Extract `mac_say_synthesizer.py` from `tools/AudioGenerator.py`**
The implementation is a refactoring of `AudioGenerator._text_to_audio()` and `_normalize_text_chunk()`, implementing the `AudioSynthesizer` protocol.

**Step 4: Extract `ffmpeg_merger.py` from `tools/AudioGenerator._merge_audio_files()`**
A standalone function `merge_audio_files(audio_files: list[Path], output_path: Path) -> bool`.

**Step 5: Write `__init__.py`**
```python
"""Audio synthesizer implementations."""
```

**Step 6: Run tests and commit**
```bash
pytest tests/infrastructure/audio/ -v
git add src/pdftranslator/infrastructure/audio/ tests/infrastructure/audio/
git commit -m "feat(infrastructure): create MacSaySynthesizer and FFmpegMerger (OCP-4, SRP-7 fix)"
```

---

### Task 2.5: Repositories — Accept ConnectionPool by Injection

**Files:**
- Modify: ALL repository files in `src/pdftranslator/database/repositories/`

**Step 1: Write failing test**
```python
# tests/database/test_repo_injection.py
"""Tests that repositories accept pool by injection (DIP-3)."""
from unittest.mock import MagicMock
from pdftranslator.database.repositories.book_repository import BookRepository
from pdftranslator.database.repositories.volume_repository import VolumeRepository
from pdftranslator.database.repositories.chapter_repository import ChapterRepository


def test_book_repo_accepts_injected_pool():
    mock_pool = MagicMock()
    repo = BookRepository(pool=mock_pool)
    assert repo._pool is mock_pool


def test_volume_repo_accepts_injected_pool():
    mock_pool = MagicMock()
    repo = VolumeRepository(pool=mock_pool)
    assert repo._pool is mock_pool
```

**Step 2: Verify that repositories ALREADY accept `pool` parameter**

Most repos have `def __init__(self, pool=None)`. The fix is to make `pool` REQUIRED (no default `DatabasePool.get_instance()`), but that breaks backward compat. So:

**Strategy**: Keep the default for now, but add a deprecation warning when pool is None:
```python
import warnings

def __init__(self, pool=None):
    if pool is None:
        warnings.warn(
            "Providing pool=None is deprecated. Inject a ConnectionPool explicitly.",
            DeprecationWarning,
            stacklevel=2,
        )
        pool = DatabasePool.get_instance()
    self._pool = pool
```

**Step 3: Run all tests**
```bash
pytest tests/ --tb=short -q
```
Expected: DeprecationWarnings may appear but tests still pass.

**Step 4: Commit**
```bash
git add src/pdftranslator/database/repositories/
git commit -m "refactor: add deprecation warning for default pool in repositories (DIP-3 partial)"
```

---

### Task 2.6: Merge Phase 2

**Step 1: Run full metrics**
```bash
./scripts/refactor_metrics.sh
```

**Step 2: Merge Phase 2 to main**
```bash
git checkout main
git merge refactor/solid-phase-2 --no-ff -m "refactor: Phase 2 - infrastructure protocols implementation"
```

**Step 3: Create Phase 3 branch**
```bash
git checkout -b refactor/solid-phase-3
```

---

## Phases 3-7: Outline (Detailed tasks to be generated upon Phase 2 completion)

### Phase 3: Application Services (Tasks 3.1-3.10)
- Create `application/services/translation_service.py`
- Create `application/services/glossary_build_service.py` (decompose GlossaryManager)
- Create `application/services/audio_service.py`
- Create `application/services/document_service.py`
- Create `application/services/file_upload_service.py`
- Move API DTOs to `application/dto/`
- Fix DIP-1: GlossaryBuildService uses LLMClient not NvidiaLLM
- Fix OCP-5: Batch size calculation uses max_tokens parameter not nvidia config
- Eliminate CLI GlossaryAwareTranslator (use TranslationService)

### Phase 4: Presentation Layer (Tasks 4.1-4.9)
- Refactor CLI commands to use Application Services
- Fix N+1 query in works API
- Fix DIP-4: CLI no longer instantiates repos directly
- Fix DUP-4: Consolidate duplicated UI functions

### Phase 5: Legacy Cleanup (Tasks 5.1-5.16)
- Delete `tools/Translator.py`
- Delete `tools/TextExtractor.py`
- Delete `database/models.py` bridge
- Delete `database/services/glossary_manager.py`
- Delete `database/services/vector_store.py`
- Fix FRG-1: named columns in repositories
- Fix MOD-2: VolumeRepository RETURNING glossary columns
- Fix MOD-3: GlossaryRepository maps `notes`

### Phase 6: TTS Module (Tasks 6.1-6.10)
- Create `MlxAudioSynthesizer`
- Create `FishSpeechSynthesizer`
- Add feature flag `tts.engine`
- Create `AudioSynthesizerFactory`
- CLI `--engine` flag

### Phase 7: Validation (Tasks 7.1-7.10)
- Full regression testing
- SOLID compliance audit
- Documentation update
- Final tag

---

## Execution Notes

- Each task follows TDD: write test → verify fail → implement → verify pass → commit
- Run `./scripts/refactor_metrics.sh` after every 2-3 tasks
- Never modify more than 3 modules per commit
- Keep backward-compatible re-exports until Phase 5
- If tests fail unexpectedly, STOP and investigate before continuing
