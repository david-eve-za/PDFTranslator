# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Sprint 2.2: Translation Service HTTP Microservice (v0.5.0)
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

