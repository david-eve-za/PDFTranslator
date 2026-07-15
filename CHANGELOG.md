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
- Sprint 1.4: Event Schemas (CloudEvents + Avro) (v0.4.0)
  - Avro schemas for core domain events: WorkCreated, DocumentExtracted, GlossaryBuilt, TranslationCompleted, AudioGenerated, JobStatusChanged
  - CloudEvents 1.0 envelope specification with trace context propagation
  - Schema Registry configuration (Apicurio/Confluent) with BACKWARD compatibility
  - Python event client library with Avro serialization (fastavro + cloudevents-sdk)
  - Go/TypeScript code generation scaffolding
  - GitOps-ready schema registration scripts
  - Event versioning strategy and migration patterns
  - Contract tests for schema validation

### Added
- Sprint 1.3: Translation Service Read-Only API (v0.3.0)
  - TranslationJob aggregate root with state machine (pending→queued→in_progress→completed/failed/paused/cancelled)
  - Segment entity for translation unit management
  - GlossaryReference value object for glossary linking
  - Repository protocols (TranslationJobRepository, SegmentRepository) with UnitOfWork
  - SQLite implementations with JSON glossary_refs storage
  - FastAPI routes: GET/POST /jobs, GET /jobs/{id}/segments, PUT /jobs/{id}/status
  - Health endpoints: /health, /ready
  - Pact contract tests for Angular frontend compatibility
  - Database migrations (translation_jobs, translation_segments tables)

---

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

## [v0.0.0] - 2026-07-01

### Added
- Repository initialization
- Basic project structure## [v0.1.0] - 2026-07-12

### Added
- CHANGELOG.md with Keep a Changelog format
- .gitmessage template for Conventional Commits
- commitlint.config.js for commit message validation
- docs/WORK_PLAN_CUPID.md: Full 22-sprint CUPID microservices migration plan
- docs/WORK_PLAN_CUPID_MICROSERVICES.md: Detailed sprint breakdown with checkboxes
- scripts/changelog-update.sh: Automated changelog generator

### Changed
- Consolidated all feature/refactor branches into main
- Cleaned up 12 local branches for fresh start

### Fixed
- Database transaction commits in connection context managers
- DATABASE_PATH env var support for database location
- Glossary Rich Progress context manager for Live display
- Datetime field parsing across repositories
- Table initialization on first connection
- TokenChunkCalculator review issues
- Adaptive token chunk sizing
- Token chunking fields in NvidiaConfig

### Documentation
- Token chunking optimization implementation plan
- Token chunking strategy design spec

