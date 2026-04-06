# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
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
- **PDFAgent.py converted to Typer**:
  - Replaced argparse with Typer for modern CLI experience
  - Added Rich integration for colorful output
  - Better error handling with proper exit codes
  - Auto-install npm dependencies if node_modules missing
  - Added `--reload` flag for backend development mode
- **Project structure reorganized** from flat directory layout to `src/` layout:
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
├── src/                      # All source code
│   ├── backend/              # FastAPI backend
│   ├── cli/                  # CLI interface (Typer)
│   ├── core/                 # Shared core (config, models, exceptions)
│   ├── database/             # Database layer
│   ├── infrastructure/       # External integrations (LLM, document)
│   ├── services/             # Business logic
│   └── tools/                # Utility tools
├── frontend/                 # React frontend (unchanged)
├── tests/                    # Test suite (mirrors src/)
├── docs/                     # Documentation
├── PDFAgent.py               # Main entry point / orchestrator
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
