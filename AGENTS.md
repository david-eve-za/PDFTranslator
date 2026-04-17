# AGENTS.md - PDFTranslator Project Guidelines

## Project Overview

PDFTranslator is a Python 3.11 application for translating PDF/EPUB documents using LLM backends (NVIDIA, Gemini, Ollama). It features a CLI interface built with Typer, PostgreSQL database with pgvector for glossary management, and AI-powered translation with glossary-aware post-processing.

## Project Structure

```
PDFTranslator/
├── src/                      # All source code
│   ├── backend/              # FastAPI backend
│   │   ├── api/              # API routes
│   │   └── main.py           # FastAPI app entry point
│   ├── cli/                  # CLI interface (Typer)
│   │   ├── commands/         # CLI commands
│   │   ├── services/         # CLI-specific services
│   │   ├── ui/               # CLI UI components
│   │   ├── app.py            # Typer app
│   │   └── __main__.py       # python -m src.cli
│   ├── core/                 # Shared core functionality
│   │   ├── config/           # Configuration (Pydantic Settings)
│   │   ├── models/           # Domain models
│   │   └── exceptions/       # Custom exceptions
│   ├── database/             # Database layer
│   │   ├── repositories/     # Repository pattern
│   │   ├── schemas/          # SQL schemas
│   │   ├── services/         # Database services
│   │   ├── connection.py     # Connection pool
│   │   └── models.py         # Data models
│   ├── infrastructure/       # External integrations
│   │   ├── llm/              # LLM implementations (NVIDIA, Gemini, Ollama)
│   │   └── document/         # Document processing (Docling)
│   ├── services/             # Business logic services
│   │   ├── translator.py     # Translation service
│   │   └── glossary_translator.py
│   └── tools/ # Utility tools
│       ├── AudioGenerator.py
│       ├── Translator.py
│       └── TextExtractor.py
├── frontend/ # Angular frontend (located at src/pdftranslator/frontend/)
│   ├── src/ # Angular source
│   ├── public/ # Static assets
│   └── package.json
├── tests/                    # Test suite (mirrors src/)
│   ├── backend/
│   ├── cli/
│   ├── core/
│   ├── database/
│   └── infrastructure/
├── docs/                     # Documentation
│   └── plans/                # Design documents
├── PDFAgent.py               # MAIN ENTRY POINT - Multi-mode orchestrator
├── pyproject.toml            # Project configuration
├── README.md
├── CHANGELOG.md
└── AGENTS.md
```

## Entry Point - PDFAgent.py

The project uses `PDFAgent.py` as a multi-mode orchestrator built with Typer CLI:

```bash
# Show help
python PDFAgent.py --help

# CLI mode - Run CLI commands
python PDFAgent.py cli translate document.pdf
python PDFAgent.py cli split document.pdf --output ./output

# Backend mode - Start FastAPI backend
python PDFAgent.py backend
python PDFAgent.py backend --host 0.0.0.0 --port 8000
python PDFAgent.py backend --reload  # Development mode with auto-reload

# Frontend mode - Start Angular frontend
python PDFAgent.py frontend

# Development mode - Start both backend + frontend
python PDFAgent.py dev
python PDFAgent.py dev --host localhost --port 8080
```

### Available Commands

| Command | Description | Options |
|---------|-------------|---------|
| `cli` | Run CLI commands for PDF translation and processing | Pass-through to src.cli.app |
| `backend` | Start FastAPI backend server | `--host, -h`, `--port, -p`, `--reload, -r` |
| `frontend` | Start Angular frontend development server | Auto-installs npm deps if needed |
| `dev` | Start both backend + frontend for development | `--host, -h`, `--port, -p` |

### Short Flags

- `-h, --host` - Host address to bind (default: 0.0.0.0)
- `-p, --port` - Port number for server (default: 8000)
- `-r, --reload` - Enable auto-reload for backend development

## Build/Test/Lint Commands

```bash
# Run all tests
pytest

# Run a single test file
pytest tests/test_nvidia_ai.py

# Run a single test function
pytest tests/test_nvidia_ai.py::test_nvidia_ai_call_model

# Run tests with coverage
pytest --cov=. --cov-report=term-missing

# Run tests in a specific directory
pytest tests/database/

# Run tests matching a pattern
pytest -k "test_chapter"

# Run tests with verbose output
pytest -v

# Run tests with print statements visible
pytest -s

# Lint with ruff (if installed)
ruff check .

# Format with ruff (if installed)
ruff format .

# Type check with mypy (if installed)
mypy .
```

## Environment Setup

```bash
# Create conda environment
conda env create -f environment.yml
conda activate PDFTranslator

# Or install dependencies with pip
pip install -r requirements.txt  # If available

# Set required environment variables
export NVIDIA_API_KEY=nvapi-xxx  # For NVIDIA backend
export GOOGLE_API_KEY=xxx        # For Gemini backend
export DB_HOST=localhost
export DB_PORT=5432
export DB_NAME=pdftranslator
export DB_USER=postgres
export DB_PASSWORD=yourpassword
```

## Code Style Guidelines

### Imports

```python
# Standard library first
import logging
import re
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any

# Third-party libraries second
import pytest
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings
from unittest.mock import MagicMock, patch

# Local imports last (absolute imports preferred)
from config.settings import Settings
from config.llm import LLMProvider, BCP47Language
from database.models import Work, Volume, Chapter
from infrastructure.llm.protocol import LLMClient
```

### Formatting

- Line length: 88 characters (Black default, Ruff default)
- Use double quotes for strings
- Use trailing commas in multi-line collections
- No comments on code unless absolutely necessary
- Docstrings: Use triple double quotes with description

### Type Annotations

```python
# Always use type hints for function arguments and returns
def translate_text(self, text: str, source_lang: str, target_lang: str) -> str:
    ...

# Use Optional for nullable types
def get_by_id(self, id: int) -> Optional[Chapter]:
    ...

# Use list[str], dict[str, Any] (lowercase) for generic types
def process_chunks(self, chunks: list[str]) -> dict[str, Any]:
    ...

# Use Union with | operator (Python 3.10+)
def get_config(self) -> GeminiConfig | NvidiaConfig | OllamaConfig:
    ...

# Use Protocol for duck typing
from typing import Protocol, runtime_checkable

@runtime_checkable
class LLMClient(Protocol):
    def call_model(self, prompt: str) -> str: ...
```

### Naming Conventions

```python
# Classes: PascalCase
class ChapterRepository:
    class GlossaryPostProcessor:

# Functions/Methods: snake_case
def translate_text(self, text: str) -> str:
def get_by_volume(self, volume_id: int) -> list[Chapter]:

# Variables: snake_case
chapter_count = 10
translated_text = ""

# Constants: UPPER_SNAKE_CASE
SCOPE_ALL_BOOK = "All Book"
DEFAULT_OUTPUT_SUBDIR = "audiobooks"
VALID_EXTENSIONS = {".pdf", ".epub"}

# Private attributes/methods: prefix with underscore
self._settings = settings
def _load_prompt_template(self) -> str:

# Protected for internal use: single underscore
def _get_iterator(self, chunks: list[str]):

# Properties: no parentheses, use @property
@property
def success(self) -> bool:
    return len(self.errors) == 0
```

### Dataclasses and Models

```python
# Use dataclasses for simple data containers
@dataclass
class TranslationResult:
    original_chunks: int
    translated_chunks: int
    text: str
    errors: list[str] = field(default_factory=list)

    @property
    def success(self) -> bool:
        return len(self.errors) == 0

# Use Pydantic for configuration and validation
class NvidiaConfig(BaseModel):
    model_name: str = Field(default="mistralai/mistral-large")
    temperature: float = Field(default=0.2, ge=0.0, le=2.0)
    max_output_tokens: int = Field(default=4096, gt=0)
```

### Error Handling

```python
# Use custom exceptions from database/exceptions.py
from database.exceptions import (
    DatabaseError,
    ConnectionError,
    QueryError,
    EntityNotFoundError,
    DuplicateEntityError,
)

# Raise specific exceptions
def get_by_id(self, id: int) -> Chapter:
    result = self._fetch_one(query, (id,))
    if result is None:
        raise EntityNotFoundError(f"Chapter with id {id} not found")
    return result

# Log errors before raising or returning
logger.error(f"Error translating chunk {index}: {e}")
errors.append(f"Chunk {index}: {str(e)}")

# Return error markers for partial failures
translated_parts.append(self._ERROR_CHUNK_MARKER.format(index=index))
```

### Testing Patterns

```python
# Use pytest fixtures for setup
@pytest.fixture
def mock_pool():
    return MagicMock()

@pytest.fixture(autouse=True)
def reset_database_pool():
    DatabasePool.reset_instance()
    yield
    DatabasePool.reset_instance()

# Use skipif for conditional tests
@pytest.mark.skipif(
    os.environ.get("NVIDIA_API_KEY", "").startswith("nvapi-") is False,
    reason="NVIDIA_API_KEY not set",
)
def test_nvidia_ai_call_model():
    ...

# Mock external dependencies
def test_translate_chunk(mock_pool, mock_connection):
    mock_connection[1].fetchall.return_value = [...]
    repo = ChapterRepository(pool=mock_pool)
    result = repo.get_by_volume(1)
    assert len(result) == 2
```

### Dependency Injection

```python
# Accept dependencies in constructor
class TranslatorService:
    def __init__(
        self,
        llm_factory: LLMFactory,
        settings: Settings | None = None,
    ):
        self._llm_factory = llm_factory
        self._settings = settings or Settings.get()

# Use factory pattern for LLM clients
class LLMFactory:
    def create(self) -> LLMClient:
        if self._settings.agent == LLMProvider.NVIDIA:
            return NvidiaLLM(self._settings)
        ...
```

## Project Structure

```
PDFTranslator/
├── cli/                    # CLI commands (Typer)
│   ├── app.py             # Main app entry point
│   ├── commands/          # Individual commands
│   └── services/          # CLI-specific services
├── config/                 # Configuration (Pydantic Settings)
│   ├── settings.py        # Main settings singleton
│   ├── llm.py            # LLM provider configs
│   ├── database.py       # Database settings
│   └── paths.py          # Path configurations
├── database/               # Database layer
│   ├── models.py          # Data models/dataclasses
│   ├── repositories/      # Repository pattern
│   ├── services/          # Database services
│   ├── connection.py      # Connection pool
│   └── exceptions.py      # Custom exceptions
├── infrastructure/         # External integrations
│   └── llm/               # LLM implementations
│       ├── base.py        # Abstract base class
│       ├── protocol.py    # LLMClient protocol
│       └── factory.py     # LLM factory
├── services/               # Business logic services
├── tools/                  # Utility tools
├── tests/                  # Test suite
│   ├── database/          # Database tests
│   └── cli/               # CLI tests
└── GlobalConfig.py        # DEPRECATED: Use config.settings
```

## Key Patterns

### Settings Singleton

```python
# Use Settings.get() for singleton access
settings = Settings.get()

# Reset in tests
Settings.reset()
```

### Repository Pattern

```python
class ChapterRepository(BaseRepository[Chapter]):
    def get_by_id(self, id: int) -> Optional[Chapter]:
        ...

    def get_by_volume(self, volume_id: int) -> list[Chapter]:
        ...
```

### Protocol for Duck Typing

```python
@runtime_checkable
class LLMClient(Protocol):
    def call_model(self, prompt: str) -> str: ...
```

## Important Notes

- `GlobalConfig` is DEPRECATED: Use `config.settings.Settings` instead
- Database uses psycopg with connection pooling (psycopg_pool)
- pgvector is used for semantic search/glossary matching
- All LLM configs use Pydantic with Field validators
- CLI uses Typer with Rich for beautiful output
- Use `Settings.reset()` in tests to avoid singleton pollution
- **Frontend is Angular (not React)** - located at `src/pdftranslator/frontend/`
- **Database migrations**: SQL schemas are in `src/pdftranslator/database/schemas/`. When adding new columns, you must run the migration manually or the app will fail with "column does not exist" errors.

## Database Migrations

When adding new database columns or tables:

1. Create a new migration file in `src/pdftranslator/database/schemas/` with sequential numbering (e.g., `014_xxx.sql`)
2. Run the migration against your database:
   ```bash
   # Using psql
   psql -h localhost -U postgres -d pdftranslator -f src/pdftranslator/database/schemas/014_xxx.sql
   
   # Or using Python
   python -c "
   from pdftranslator.database.connection import DatabasePool
   pool = DatabasePool.get_instance()
   with open('src/pdftranslator/database/schemas/014_xxx.sql') as f:
       with pool.get_sync_pool().connection() as conn:
           conn.execute(f.read())
   "
   ```

## Frontend Architecture

The frontend is built with **Angular 17+** (standalone components) and uses:

- **SCSS** for styling with CSS variables defined in `styles.scss`
- **Signals** for reactive state management
- **ng2-charts** for chart visualizations

### Key CSS Variables

The project uses a custom design system. Main variables defined in `styles.scss`:

```scss
:root {
  --primary: #8B4513;
  --accent: #C9A961;
  --text: var(--ink);
  --surface: var(--paper);
  --font-display: 'Playfair Display', Georgia, serif;
  --font-accent: 'Cormorant Garamond', Georgia, serif;
  --radius-md: 8px;
  --transition-fast: 0.15s ease;
  // ... see styles.scss for full list
}
```

**IMPORTANT**: When creating new components, use these existing variables, not invented ones like `--color-primary`, `--font-size-base`, etc.

### Message Handling Pattern

All components that display success/error messages should follow this pattern to prevent message spam:

```typescript
// 1. Implement OnDestroy to clean up timeouts
export class MyComponent implements OnInit, OnDestroy {
  private messageTimeoutId: ReturnType<typeof setTimeout> | null = null;

  // 2. Clear timeout on destroy
  ngOnDestroy(): void {
    this.clearMessageTimeout();
  }

  private clearMessageTimeout(): void {
    if (this.messageTimeoutId) {
      clearTimeout(this.messageTimeoutId);
      this.messageTimeoutId = null;
    }
  }

  // 3. Use helper methods for messages
  private showSuccess(message: string, duration: number = 3000): void {
    this.clearMessageTimeout();
    this.errorMessage.set(null);
    this.successMessage.set(message);
    this.messageTimeoutId = setTimeout(() => {
      this.successMessage.set(null);
      this.messageTimeoutId = null;
    }, duration);
  }

  private showError(message: string): void {
    this.clearMessageTimeout();
    this.successMessage.set(null);
    this.errorMessage.set(message);
  }
}
```

This pattern ensures:
- Only one message is shown at a time
- Timeouts are properly cancelled when showing new messages
- No memory leaks when components are destroyed
- No message accumulation issues

### Frontend Feature Modules

The frontend is organized into feature modules under `src/app/features/`:

- **Dashboard**: Stats, charts, recent activity
- **Library**: Work browser with volume/chapter progress
- **Glossary**: Term management with AI-powered entity extraction
- **Split**: Chapter marker insertion tool
- **Settings**: Configuration and substitution rules
- **Translate**: Translation interface

Each feature module contains:
- `*.component.ts` - Component logic with signals
- `*.component.html` - Template with Angular control flow (`@if`, `@for`)
- `*.component.scss` - Styles using design system variables
