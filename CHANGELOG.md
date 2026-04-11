# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added - Frontend Mock Data Integration (2026-04-11)

#### Mock Data Implementation
- **Angular InMemoryWebAPI** configured for development:
  - Local mock data for all entities (works, volumes, chapters, glossary)
  - Simulates backend API responses without running server
  - 500ms delay to simulate real network latency
  - Automatic HTTP request interception

#### Mock Data Entities
- **Languages**: 12 supported languages (en-US, es-MX, fr-FR, de-DE, etc.)
- **Providers**: 3 LLM providers (NVIDIA, Gemini, Ollama)
- **Works**: 3 sample works with translation progress
- **Volumes**: 5 volumes across works
- **Chapters**: 5 chapters with translation status
- **Glossary Terms**: 5 glossary entries with entity types
- **Recent Activities**: 5 activity log entries

#### Core Services Created
- `WorkService` - CRUD operations for works
- `VolumeService` - Volume management by work
- `GlossaryService` - Glossary term CRUD with filters
- `DashboardService` - Recent activity fetching
- `TranslationConfigService` - Languages and providers

#### Models Implemented
- `Work`, `WorkCreate`, `WorkUpdate`
- `Volume`, `VolumeCreate`
- `Chapter`, `ChapterCreate`, `ChapterType`, `TranslationStatus`
- `GlossaryTerm`, `GlossaryTermCreate`, `GlossaryTermUpdate`, `EntityType`
- `TranslationProgress`, `TranslationStartRequest`
- `DashboardStats`, `RecentActivity`, `TranslationChartData`

#### Bug Fixes
- Fixed `ECONNREFUSED` error when backend not running
- Mock data now serves `/api/languages` and `/api/providers` endpoints
- InMemoryWebAPI compatible with Angular 21 (version 0.21.0)

### Added - Frontend Migration to Angular (2026-04-10)

#### Frontend Migration
- **Replaced React frontend with Angular 17+**:
  - Standalone components (no NgModules)
  - Signal-based reactive state management
  - TypeScript strict mode
  - SCSS styling with dark/light theme support
  - Lazy-loaded feature modules

#### New Angular Features
- **Translation Module**:
  - Drag-and-drop file upload for PDF/EPUB
  - Language selector with search functionality
  - LLM provider selection (NVIDIA, Gemini, Ollama)
  - Real-time progress indicator with animations
  - Error handling and success states
- **Glossary Module**:
  - Full CRUD operations for glossary terms
  - Search and filter by language pair
  - Context support for translations
  - Responsive table layout

#### Backend API Enhancements
- **New endpoints** for frontend integration:
  - `GET /api/languages` - List supported languages
  - `GET /api/providers` - List available LLM providers
  - `GET /api/glossary` - List glossary terms with filters
  - `POST /api/glossary` - Create glossary term
  - `PUT /api/glossary/{id}` - Update glossary term
  - `DELETE /api/glossary/{id}` - Delete glossary term

#### Configuration Updates
- **CORS configuration** updated to support Angular dev server:
  - Added `http://localhost:4200` to allowed origins
- **PDFAgent.py** updated for Angular:
  - Changed `npm run dev` to `npm start` (Angular CLI default)
  - Updated frontend path to `src/pdftranslator/frontend`
  - Fixed frontend and dev commands

#### Styling & Design
- **Distinctive typography**: Google Fonts (Outfit for headings, DM Sans for body)
- **Bold color scheme** with CSS custom properties
- **Dark/Light theme** with smooth transitions and localStorage persistence
- **Responsive design** for mobile and desktop
- **Accessibility compliance** (a11y standards)

### Changed
- Frontend technology stack: React → Angular 17+
- Build tool: Vite → Angular CLI
- Package manager scripts updated for Angular

### Fixed
- Frontend path resolution in PDFAgent.py
- Missing `npm start` command for Angular
- CORS issues with Angular development server

### Added - Modern Python Structure Refactoring (2025-04-10)

#### New Package Structure
- **Created `pdftranslator` package** under `src/`:
  - All code now under `src/pdftranslator/` (standard Python 2025 layout)
  - Frontend integrated into `src/pdftranslator/frontend/`
  - Clean separation: backend, cli, core, database, infrastructure, services, tools

#### Configuration & Standards
- **Modern `pyproject.toml`** configuration:
  - Project metadata (name, version 0.2.0, description)
  - Dependencies and optional dependencies (dev, gemini, ollama, docling)
  - Entry points: `pdftranslator` and `pdfagent` commands
  - Tool configurations: ruff, mypy, pytest, coverage
  - Package discovery and data files
- **MIT License** added
- **`.python-version`** file (Python 3.11)
- **Entry points**:
  - `src/pdftranslator/__init__.py` with version metadata
  - `src/pdftranslator/__main__.py` as main entry point
  - Support for: `python -m pdftranslator`, `pdftranslator` command

#### Import Updates
- **Updated 181 import statements**:
  - Old: `from src.module` → New: `from pdftranslator.module`
  - All modules now use new package namespace
- **Updated test mocks**:
  - All `patch("src.")` → `patch("pdftranslator.")`

#### Directory Cleanup
- **Removed duplicate directories** from root:
  - `backend/` (moved to `src/pdftranslator/backend/`)
  - `config/` (moved to `src/pdftranslator/core/config/`)
  - `infrastructure/` (moved to `src/pdftranslator/infrastructure/`)
- **Removed obsolete files**:
  - `src/__init__.py` (package now under pdftranslator)
  - `mistral-large-3-675b-instruct-2512/` (tokenizer cache)
  - `PDFAgent.log` (log file)

### Changed - Backward Compatibility

#### Entry Point Migration
- **`PDFAgent.py`** now deprecated:
  - Shows deprecation warning
  - Delegates to new `pdftranslator` package
  - Recommended new usage: `python -m pdftranslator` or `pdftranslator` command
- **New entry points** available:
  - `pdftranslator cli translate document.pdf`
  - `pdftranslator backend --port 8080`
  - `pdftranslator frontend`
  - `pdftranslator dev`
  - `python -m pdftranslator [command]`

### Migration Guide

#### For Users

**Before (Old Structure):**
```python
from src.backend.main import app
from src.core.config.settings import Settings
from src.database.models import Work
```

**After (New Structure):**
```python
from pdftranslator.backend.main import app
from pdftranslator.core.config.settings import Settings
from pdftranslator.database.models import Work
```

#### Running the Application

**Before:**
```bash
python PDFAgent.py cli translate document.pdf
python PDFAgent.py backend
```

**After (Recommended):**
```bash
# Using installed command
pdftranslator cli translate document.pdf
pdftranslator backend --port 8080

# Using module execution
python -m pdftranslator cli translate document.pdf
python -m pdftranslator backend

# Backward compatible (deprecated)
python PDFAgent.py cli translate document.pdf
```

#### Installing the Package

```bash
# Development install
pip install -e .

# Or with optional dependencies
pip install -e ".[dev]"
pip install -e ".[all]"
```

### Directory Structure (After Refactoring)

```
PDFTranslator/
├── src/
│   └── pdftranslator/           # Main package
│       ├── __init__.py          # Version 0.2.0
│       ├── __main__.py          # Entry point
│       ├── backend/             # FastAPI backend
│       ├── cli/                 # CLI interface
│       ├── core/                # Core functionality
│       ├── database/            # Database layer
│       ├── infrastructure/      # External integrations
│       ├── services/            # Business logic
│       ├── tools/               # Utility tools
│       └── frontend/            # React frontend
├── tests/                       # Test suite
├── docs/                        # Documentation
├── pyproject.toml               # Modern config
├── LICENSE                      # MIT License
├── .python-version              # Python 3.11
├── README.md
├── CHANGELOG.md
├── AGENTS.md
└── PDFAgent.py                  # Deprecated entry point
```

### Fixed
- **Configuration system migration completed**:
  - Replaced all `GlobalConfig` references with `Settings.get()` throughout the codebase
  - Fixed database connection to use nested configuration (`config.database.host`, `config.database.port`, etc.)
  - Fixed vector store service to use `config.llm.nvidia.embed_model`, `config.llm.nvidia_api_key`
  - Fixed Translator to use `config.paths.translation_prompt_path`
  - Added `ProcessingSettings` for audio/video generation configuration
- **Path configuration fixed**:
  - `translation_prompt_path` now uses absolute path based on project root
  - Added `_get_project_root()` helper to dynamically resolve project directory
  - Fixed "No such file or directory: tools/translation_prompt.txt" error
  - File: `src/core/config/paths.py`
- **GlossaryEntry model field names updated**:
  - Renamed `source_term`/`target_term` to `term`/`translation` to match database schema
  - Updated `GlossaryPostProcessor` to use new field names
  - Updated backend API schemas (`GlossaryEntryResponse`, `GlossaryUpdateRequest`)
  - Fixed "'GlossaryEntry' object has no attribute 'source_term'" error
  - Files: `src/cli/services/glossary_post_processor.py`, `src/backend/api/models/schemas.py`
- **Database models restored to match PostgreSQL schema**:
  - `Work`: Added `title_translated`, `author` fields
  - `Volume`: Added `full_text`, `translated_text`, `embedding` fields
  - `Chapter`: Added `start_position`, `end_position`, `embedding` fields
  - `GlossaryEntry`: Changed `source_term`/`target_term` to `term`/`translation`, added `is_proper_noun`, `embedding`
  - Added `TermContext` and `ContextExample` models
- **Database repositories updated to match schema**:
  - `BookRepository`: Updated queries for all fields including `title_translated`, `author`
  - `VolumeRepository`: Updated to handle `full_text`, `translated_text` columns
  - `ChapterRepository`: Updated to handle `start_position`, `end_position` columns
  - `GlossaryRepository`: Updated to use `term`, `translation`, `is_proper_noun` columns
- **LLM initialization fixed**:
  - `NvidiaLLM`, `GeminiLLM`, `OllamaLLM` now receive `Settings` parameter in constructor
  - `Translator` class properly passes settings to LLM factory methods
- **Database connection string escaping**:
  - Fixed connection string format to use PostgreSQL URI format
  - Proper handling of special characters in passwords using `quote_plus`
- **Frontend compilation errors resolved**:
  - Removed deprecated `baseUrl` from tsconfig.json (TypeScript 6.0+ migration)
  - Moved path aliases to tsconfig.app.json for Vite compatibility
  - Fixed unused `get` parameter warning in fileStore.ts
  - Frontend now builds successfully without TypeScript errors
- **Frontend files restored from git history**:
  - Recovered Dashboard, components, stores, and services from commit `fa44e6d`
  - Removed duplicate git repository in frontend/ directory
  - All UI components now load correctly

### Added
- **ProcessingSettings configuration**:
  - New `src/core/config/processing.py` with audio/video generation settings
  - Fields: `input_path`, `source_lang`, `target_lang`, `output_format`, `voice`, `gen_video`, `develop_mode`
- **LLM configuration enhancements**:
  - Added `embed_model`, `rerank_model`, `rerank_top_n` to `NvidiaConfig`
  - Added `nvidia_api_key`, `google_api_key` to `LLMSettings`
- `call_model_with_temperature()` method to LLM protocol and all implementations (NVIDIA, Gemini, Ollama)
  - Allows dynamic temperature control per-request without modifying global config
  - Implements temperature override with automatic restoration for thread safety
  - Protocol: `infrastructure/llm/protocol.py`
  - Implementations: `infrastructure/llm/{nvidia,gemini,ollama}.py`
- **New project structure** following Python best practices:
  - All source code organized under `src/` directory
  - Clear separation: `src/backend/`, `src/cli/`, `src/core/`, `src/database/`, `src/infrastructure/`, `src/services/`, `src/tools/`
  - `PDFAgent.py` orchestrator for multi-mode execution
- **PDFAgent.py orchestrator with Typer CLI**:
  - Converted from argparse to Typer for better UX
  - Beautiful CLI interface with Rich formatting
  - Interactive help with examples
  - 4 commands: `cli`, `backend`, `frontend`, `dev`
  - `python PDFAgent.py cli [command]` - Run CLI commands
  - `python PDFAgent.py backend` - Start FastAPI backend (with `--reload` option)
  - `python PDFAgent.py frontend` - Start React frontend
  - `python PDFAgent.py dev` - Start both backend + frontend for development
  - Short flags: `-h` for host, `-p` for port, `-r` for reload

### Changed
- **LLM timeout configuration**:
  - Added default timeout of 30 minutes (1800 seconds) to all LLM implementations
  - `NvidiaLLM`: Uses `request_timeout` from config or defaults to 30 minutes
  - `GeminiLLM`: Uses `request_timeout` from config or defaults to 30 minutes
  - `OllamaLLM`: Added `request_timeout` parameter with 30 minute default
  - Prevents indefinite hangs on slow or unresponsive API calls
  - Files: `src/infrastructure/llm/{nvidia,gemini,ollama}.py`
- **Configuration system modernized**:
  - Migrated from `GlobalConfig` (deprecated singleton) to `Settings` (Pydantic-based)
  - Configuration now uses nested models: `settings.database.host`, `settings.llm.nvidia.model_name`
  - Environment variables use `__` separator for nested values (e.g., `DATABASE__PASSWORD`)
- **PDFAgent.py converted to Typer**:
  - Replaced argparse with Typer for modern CLI experience
  - Added Rich integration for colorful output
  - Better error handling with proper exit codes
  - Auto-install npm dependencies if node_modules missing
  - Added `--reload` flag for backend development mode
- **Project structure reorganized** from flat directory layout to `src/` layout:
  - Old: `backend/`, `cli/`, `config/`, `database/`, etc. in root
  - New: `src/backend/`, `src/cli/`, `src/core/config/`, `src/database/`, etc.
- **Import paths updated** throughout the codebase:
  - `from config.` → `from src.core.config.`
  - `from database.` → `from src.database.`
  - `from infrastructure.` → `from src.infrastructure.`
  - `from services.` → `from src.services.`
  - `from tools.` → `from src.tools.`
- **DoclingConfig defaults optimized for macOS development**:
  - `enable_ocr`: `True` → `False` (disabled by default to improve performance)
  - `accelerator_device`: `"auto"` → `"mps"` (Metal Performance Shaders for Apple Silicon)
- **DoclingExtractor accelerator handling improved**:
  - Direct enum lookup with case-insensitive support
  - Graceful fallback to CPU on invalid device configuration
  - Better error logging for debugging
  - File: `infrastructure/document/docling_extractor.py`
- **GlobalConfig.py removed** (deprecated):
  - Use `src.core.config.settings.Settings` instead
  - All references updated to use new Pydantic Settings

### Removed
- `GlobalConfig.py` - deprecated singleton configuration
- `llm/` directory - duplicated infrastructure/llm/
- Deprecated import patterns and legacy code

### Fixed
- **Section classifier now handles LLM failures gracefully**:
  - Added fallback classification when LLM returns invalid JSON
  - Maintains operation even with malformed responses
  - File: `tests/test_document_chapter_splitter_v2.py`

### Tests
- Updated `tests/database/test_vector_store.py` to use `Settings` instead of `GlobalConfig`
- Added comprehensive test suite for accelerator device configuration:
  - `test_docling_extractor_device_auto()` - Auto device detection
  - `test_docling_extractor_device_cpu()` - CPU-only mode
  - `test_docling_extractor_device_cuda()` - CUDA/NVIDIA GPU mode
  - `test_docling_extractor_device_mps()` - Apple Metal mode
  - `test_docling_extractor_device_case_insensitive()` - Case handling
  - `test_docling_extractor_invalid_device_rejected_by_config()` - Validation
  - File: `tests/infrastructure/document/test_docling_extractor.py`
- Added enhanced section classifier tests with Roman numeral conversion:
  - File: `tests/test_section_classifier_enhanced.py`
- Added integration tests for real LLM classification:
  - File: `tests/test_section_classifier_integration.py`

### Dependencies
- Added `environment.yml` updates for development environment consistency

## Directory Structure

### New Structure (after refactor)
```
PDFTranslator/
├── src/                    # All source code
│   ├── backend/            # FastAPI backend
│   ├── cli/                # CLI interface (Typer)
│   ├── core/               # Shared core (config, models, exceptions)
│   ├── database/           # Database layer
│   ├── infrastructure/     # External integrations (LLM, document)
│   ├── services/           # Business logic
│   └── tools/              # Utility tools
├── frontend/               # React frontend (unchanged)
├── tests/                  # Test suite (mirrors src/)
├── docs/                   # Documentation
├── PDFAgent.py             # Main entry point / orchestrator
├── CHANGELOG.md
├── README.md
└── AGENTS.md
```

## Rollback Instructions

If you need to rollback this commit:

```bash
# View the commit
git show <commit-hash>

# Soft rollback (keep changes in working directory)
git reset --soft HEAD~1

# Hard rollback (discard all changes) - USE WITH CAUTION
git reset --hard HEAD~1

# Or revert by creating a new commit that undoes changes
git revert <commit-hash>
```

For this refactoring, you can also switch back to the previous branch:
```bash
git checkout main
# Or keep the refactor branch for later
git checkout refactor/src-directory-structure
```

## [0.1.0] - 2025-01-XX

### Added
- Initial project structure
- PDF/EPUB document translation using LLM backends
- CLI interface with Typer
- PostgreSQL database with pgvector for glossary management
- Support for NVIDIA, Gemini, and Ollama LLM providers
