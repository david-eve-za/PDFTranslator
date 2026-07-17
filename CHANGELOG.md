# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [v0.7.0] - 2026-07-14

### Added
- Sprint 2.4: Contract + Load Tests Phase 2
  - **Contract Tests (43 tests)**: Full API contract coverage for text processing library
    - TextChunker: deterministic chunking, all 4 strategies (tokens/sentences/paragraphs/characters)
    - Tokenizer: singleton cache, encode/decode roundtrip, token counting consistency
    - OverlapHandler: overlap application/removal with metadata tracking
    - TextNormalizer: NFKC/NFD unicode, lowercase, control chars, dashes, ellipsis, whitespace
    - ChunkConfig/NormalizationConfig: validation, factories (for_translation/for_embedding), serialization
  - **Load Tests (15 tests)**: Performance baselines with latency percentiles
    - TextChunker: sequential/concurrent for translation/embedding configs, all strategies
    - Tokenizer: encoding performance under load, roundtrip consistency
    - TextNormalizer: concurrent translation config normalization
    - OverlapHandler: sequential and concurrent overlap application
    - Full Pipeline: normalize→chunk→overlap under concurrent load (p50/p95/p99)
    - Memory Stability: sustained operations without leaks (100+ iterations)

### Changed
- Consolidated NormalizationConfig into single source of truth in models.config (eliminated duplicate in core/normalizer.py)
- Updated core.normalizer to use models.config with enum fields (NormalizationForm)
- Fixed pytest configuration for proper src-layout test discovery
- Added load/slow markers and pact-python, locust to dev dependencies

### CUPID
- Predictable: Deterministic chunking behavior verified across all strategies
- Composable: Modular test components (contract, load, pipeline) can run independently
- Unix Philosophy: Each test targets one behavior, pure functions with no side effects
- Idiomatic: Uses pytest fixtures, parametrize, standard assertions
- Domain-Focused: Tests mirror translation/embedding use cases

## [v0.8.0] - 2026-07-14

### Added
- Sprint 3.1: Job Orchestrator Temporal Workflows
  - **Temporal Workflows** for durable translation job orchestration
    - `TranslationWorkflow`: 5-stage pipeline (Detect → Segment → Translate → QC → Store)
    - `ResumeTranslationWorkflow`: Resume from failed stage with deterministic replay
  - **5 Temporal Activities** (Unix Philosophy - single responsibility):
    - `detect_language_activity`: Language detection with text statistics
    - `segment_text_activity`: Sentence-based segmentation with configurable max length
    - `translate_segments_activity`: LLM-powered segment translation
    - `quality_check_activity`: Completeness, fluency, consistency, formatting checks
    - `store_translations_activity`: Persistence of translated segments
  - **Test Coverage (15 tests)**:
    - 12 unit tests for activities (all 5 stages)
    - 3 integration tests for workflow execution and resume

### Changed
- Added `temporalio>=1.0.0` as production dependency for workflow orchestration

### CUPID
- Predictable: Deterministic workflow replay via Temporal event sourcing
- Domain-Focused: Workflows model translation job lifecycle (detect→store)
- Composable: Activities are independently testable and reusable
- Unix Philosophy: Each activity does one thing well with explicit inputs/outputs
- Idiomatic: Uses Temporal workflow/activity patterns with retry policies

## [v0.6.0] - 2026-07-14

### Added
- Sprint 2.3: Text Processing Library + CLI (v0.1.0)
  - **TextChunker** with 4 splitting strategies: tokens, sentences, paragraphs, characters
  - **OverlapHandler** for context preservation between consecutive chunks
  - **TextNormalizer** with Unicode normalization (NFC/NFD/NFKC/NFKD), smart quotes/dashes/ellipsis
  - **Tokenizer** wrapper with tiktoken caching (cl100k_base, o200k_base, p50k_base, r50k_base)
  - **CLI: pdftranslator-text** with commands: chunk, tokenize, analyze, config
  - Deterministic token-bounded chunking with configurable overlap
  - Stdin/stdout pipeline support for Unix philosophy composition
  - Rich output formatting: JSON, JSONL, text, tables
  - Factory configs: for_translation(), for_embedding()
  - CUPID-compliant: domain models with invariants, pure functions, typed protocols

## [v0.5.0] - 2026-07-13

### Added
- Sprint 2.2: Translation Service HTTP Microservice
  - 5-stage translation pipeline: Detect → Segment → Translate → Quality-Check → Store
  - Individual stage endpoints for independent testing/debugging
  - Pipeline management: /pipelines/run, GET /pipelines/{job_id}, POST /pipelines/{job_id}/resume
  - Language detection with confidence scoring and text statistics
  - Sentence-based text segmentation with configurable max length
  - LLM-powered translation with configurable provider/model/temperature
  - Quality checks: completeness, terminology, fluency, consistency, formatting
  - Translation persistence with automatic job completion
  - Pipeline state tracking (pending→running→completed/failed/paused/cancelled)
  - Database migrations for translation_pipelines and translation_pipeline_stages tables
  - Contract tests for all pipeline endpoints

## [Unreleased]

### Added
- Sprint 3.2: Job Orchestrator API Integration
  - REST endpoints for Temporal workflow execution and monitoring
  - POST /jobs/{job_id}/run - start translation pipeline
  - GET /jobs/{job_id}/status - query workflow status
  - POST /jobs/{job_id}/resume - resume from failed stage

---

## [v0.1.0] - 2026-07-12

### Added
- Initial project structure for PDFTranslator
- CLI commands for document processing, glossary management, chapter splitting
- FastAPI backend with Angular 17+ frontend
- LLM integration: NVIDIA NIM, Google Gemini, Ollama
- SQLite database with WAL mode for local development
- Glossary system with semantic search via pgvector
- Document extraction using PyMuPDF and ebooklib
- Chapter splitting with interactive web UI
- Audiobook generation with macOS `say` command
- Docker Compose for local development stack

---

