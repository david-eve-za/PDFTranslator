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

### Changed
- **DoclingConfig defaults optimized for macOS development**:
  - `enable_ocr`: `True` → `False` (disabled by default to improve performance)
  - `accelerator_device`: `"auto"` → `"mps"` (Metal Performance Shaders for Apple Silicon)
- **DoclingExtractor accelerator handling improved**:
  - Direct enum lookup with case-insensitive support
  - Graceful fallback to CPU on invalid device configuration
  - Better error logging for debugging
  - File: `infrastructure/document/docling_extractor.py`

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

## [0.1.0] - 2025-01-XX

### Added
- Initial project structure
- PDF/EPUB document translation using LLM backends
- CLI interface with Typer
- PostgreSQL database with pgvector for glossary management
- Support for NVIDIA, Gemini, and Ollama LLM providers
