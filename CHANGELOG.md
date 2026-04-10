# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

#### Feature: Document Workflow UI (Merged from `feature/document-workflow-ui`)
- **FastAPI backend** with file upload endpoint
  - File: `backend/api/routes/files.py`
  - File: `backend/api/models/schemas.py`
  - Entry point: `backend/main.py`
- **React frontend** with Vite + TypeScript
  - Dashboard page with task management
  - File upload with drag-and-drop
  - Task screens for Glossary, Split Chapters, Translation
  - Error boundary for graceful error handling
  - Spinner and loading states
- **State management** with Zustand
  - File stores: `frontend/src/stores/fileStore.ts`
  - Task stores: `frontend/src/stores/taskStore.ts`
- **UI components** with shadcn/ui
  - Button, Card, Badge, Input, Spinner
  - FileCard, FileDropZone, TaskBadge
- **TypeScript types** for type safety
  - File, Task, Glossary, Chapter, Audio, Translation types
- **API service layer** with mock data support
  - File: `frontend/src/services/api.ts`
  - Config: `frontend/src/services/config.ts`
- **LLM temperature control** for per-request customization
  - Method: `call_model_with_temperature()` in all LLM implementations
  - Dynamic temperature override with automatic restoration
  - Files: `infrastructure/llm/{nvidia,gemini,ollama}.py`
- **Docling extractor improvements**
  - Optimized defaults for macOS development (OCR disabled, MPS accelerator)
  - Better accelerator device handling with graceful fallback
  - File: `infrastructure/document/docling_extractor.py`

#### Feature: Build-Glossary Optimization (Merged from `feature/optimize-build-glossary-hybrid`)
- **LLM validation** for entity filtering and classification
  - Filters false positives from NLTK extraction
  - Improves entity type classification
  - Provides initial translations during validation
  - File: `src/database/services/glossary_manager.py`
- **Auto-batching** for translations to avoid truncation
  - Intelligent batch size calculation (~60-80 entities for validation)
  - Batch size: ~90-100 entities for translation
  - Reuses translations from validation phase (optimization)
  - Handles 500+ entities without truncation
- **EntityCandidate model enhanced**
  - Added `translation: Optional[str]` field
  - Added `validated: bool` field
  - File: `src/database/models.py`
- **Test suite** for validation and batching
  - 8 tests for LLM validation
  - 13 tests for auto-batching
  - All 21 tests passing
  - Files: `tests/database/services/test_glossary_manager_*.py`

### Changed

- **Project structure reorganized** under `src/` directory
  - All source code moved to `src/`
  - Clear separation: backend, cli, core, database, infrastructure, services, tools
- **Configuration system modernized**
  - Migrated from `GlobalConfig` to Pydantic `Settings`
  - Nested configuration: `settings.database.host`, `settings.llm.nvidia.model_name`
  - Environment variables use `__` separator
- **PDFAgent.py converted to Typer CLI**
  - Commands: `cli`, `backend`, `frontend`, `dev`
  - Rich formatting and beautiful output
  - Auto-install npm dependencies
- **DoclingConfig defaults optimized**
  - `enable_ocr`: disabled by default (performance)
  - `accelerator_device`: MPS for Apple Silicon

### Fixed

- Section classifier handles LLM failures gracefully
- Frontend TypeScript compilation errors resolved
- Database connection string escaping
- LLM initialization with Settings parameter

### Tests

- Comprehensive test suite for accelerator device configuration
- Enhanced section classifier tests with Roman numeral conversion
- Integration tests for real LLM classification
- Glossary manager validation and batching tests (21 tests)

---

## Branch Index for Rollback

This section documents all merged branches for easy rollback if needed.

### Active Branches (Available for Rollback)

| Branch Name | Merge Commit | Description | Rollback Command |
|-------------|--------------|-------------|------------------|
| `feature/document-workflow-ui` | `722dc8a` | FastAPI backend + React frontend with document workflow UI | `git revert 722dc8a` |
| `feature/optimize-build-glossary-hybrid` | `2713c7c` | LLM validation + auto-batching for glossary building | `git revert 2713c7c` |
| `refactor/src-directory-structure` | `19432c9` | Project reorganization under src/ directory | `git revert 19432c9` |

### Historical Branches (Already in Main History)

| Branch Name | Final Commit | Description | Status |
|-------------|--------------|-------------|--------|
| `feature/nvidia-ai-connector` | `af61db6` | NVIDIA NIM integration | Merged |
| `cleanup/remove-obsolete-directories` | `f3dbfd0` | Cleanup after src/ refactor | Merged |
| `feature/slide-video-generation` | `6c8183b` | Video generation with slides | Merged |
| `feature/service-factory-application` | `c148a5d` | Service factory pattern | Merged |

### How to Rollback

#### Option 1: Revert Merge (Recommended - Creates new commit)
```bash
# Rollback a specific feature
git revert -m 1 <merge-commit-hash>

# Example: Rollback glossary optimization
git revert -m 1 2713c7c
```

#### Option 2: Hard Reset to Previous State (Destructive)
```bash
# WARNING: This discards all commits after the target
git reset --hard <commit-hash>

# Example: Reset to before glossary optimization
git reset --hard 722dc8a
```

#### Option 3: Checkout Branch for Inspection
```bash
# View the branch state before deciding to rollback
git checkout <branch-name>

# Example: Inspect document workflow UI
git checkout feature/document-workflow-ui

# Return to main
git checkout main
```

### Branch Details

#### feature/document-workflow-ui
- **Merged**: 2026-04-10
- **Commits**: 16 commits
- **Changes**: 
  - FastAPI backend with file upload
  - React frontend with Dashboard
  - Zustand state management
  - shadcn/ui components
  - TypeScript types
  - LLM temperature control
- **Risk**: Medium - Adds new frontend/backend infrastructure
- **Dependencies**: None

#### feature/optimize-build-glossary-hybrid
- **Merged**: 2026-04-10
- **Commits**: 1 commit (ee12037)
- **Changes**:
  - LLM validation for entity filtering
  - Auto-batching for translations
  - EntityCandidate model updates
  - 21 unit tests
- **Risk**: Medium - Changes glossary building pipeline
- **Dependencies**: Requires LLM API calls (cost: ~15× more per volume)
- **Performance**: Adds ~75-150 seconds per volume

#### refactor/src-directory-structure
- **Merged**: Before document workflow
- **Commits**: Multiple
- **Changes**:
  - Reorganized project under src/
  - Updated all import paths
  - Modernized configuration system
  - Converted PDFAgent to Typer
- **Risk**: High - Major structural change
- **Dependencies**: All subsequent branches depend on this

---

## Directory Structure

### Current Structure (after all merges)
```
PDFTranslator/
├── src/                    # All source code
│   ├── backend/            # FastAPI backend
│   │   ├── api/            # API routes and models
│   │   └── main.py         # Backend entry point
│   ├── cli/                # CLI interface (Typer)
│   │   ├── commands/       # CLI commands
│   │   └── services/       # CLI services
│   ├── core/               # Shared core
│   │   ├── config/         # Configuration (Pydantic Settings)
│   │   └── models/         # Domain models
│   ├── database/           # Database layer
│   │   ├── repositories/   # Repository pattern
│   │   ├── services/       # Database services
│   │   └── connection.py   # Connection pool
│   ├── infrastructure/     # External integrations
│   │   ├── llm/            # LLM implementations (NVIDIA, Gemini, Ollama)
│   │   └── document/       # Document processing (Docling)
│   ├── services/           # Business logic services
│   └── tools/              # Utility tools
├── frontend/               # React frontend
│   ├── src/
│   │   ├── components/     # UI components
│   │   ├── pages/          # Dashboard and task screens
│   │   ├── stores/         # Zustand stores
│   │   ├── services/       # API service layer
│   │   └── types/          # TypeScript types
│   └── package.json
├── backend/                # FastAPI backend (root level)
│   ├── api/
│   └── main.py
├── tests/                  # Test suite (mirrors src/)
├── docs/                   # Documentation
│   └── plans/              # Design documents
├── PDFAgent.py             # Main entry point / orchestrator
├── CHANGELOG.md
├── README.md
└── AGENTS.md
```

---

## [0.1.0] - 2025-01-XX

### Added
- Initial project structure
- PDF/EPUB document translation using LLM backends
- CLI interface with Typer
- PostgreSQL database with pgvector for glossary management
- Support for NVIDIA, Gemini, and Ollama LLM providers
