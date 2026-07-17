# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [v0.14.0] - 2026-07-17

### Added
- Sprint 4.1: API Gateway Kong Setup
  - **Kong Declarative Configuration** (`gateway/kong/kong.yml`):
    - 5 upstream services: Catalog (8001), Glossary (8002), Translation (8003), Document (8004), Audio (8005)
    - Route definitions for all REST endpoints with proper path stripping
    - Service plugins: rate-limiting, request-transformer, correlation-id
  - **Per-Service Rate Limiting**:
    - Catalog: 100/min, 1000/hr (read-heavy)
    - Glossary: 60/min, 500/hr (moderate)
    - Translation: 30/min, 200/hr (compute-intensive)
    - Document: 10/min, 50/hr (large payloads)
    - Audio: 5/min, 20/hr (very compute-intensive)
  - **Global Plugins**:
    - CORS for frontend (localhost:4200, 8080)
    - Prometheus metrics exposition
    - Response security headers (CSP, X-Frame-Options, etc.)
    - IP restriction for admin endpoints
    - Access logging to Logstash
  - **Authentication** (Key-Auth):
    - Frontend consumer with API key
    - Admin consumer with API key
    - Webhook receiver consumer
  - **Docker Compose Stack** (`gateway/kong/docker-compose.kong.yml`):
    - Kong 3.4 with PostgreSQL 15
    - Konga UI for gateway management
    - Prometheus + Grafana for monitoring
    - Health checks and dependency ordering
  - **Monitoring**:
    - Prometheus scrape config for Kong + upstream services
    - Grafana dashboard with 9 panels (RPS, latency, error rates, connections, rate limiting)
    - Pre-configured datasources and dashboard provisioning
  - **Operations**:
    - Startup script with health checks (`start-kong.sh`)
    - Environment template (`.env.example`)
    - Comprehensive README with troubleshooting guide
  - **Security**:
    - Request size limits per service
    - Timeout budgets per service
    - Response header hardening
    - JWT/Key-Auth ready for production

### CUPID
- **Composable**: Independent service routes, reusable plugins
- **Unix Philosophy**: Each route → one service, stdin/stdout proxy model
- **Predictable**: Explicit rate limits, timeout budgets, retry policies
- **Idiomatic**: Kong declarative config, Prometheus metrics, Docker Compose
- **Domain-Focused**: Routes mirror translation domain (catalog/glossary/translation/document/audio)

## [v0.13.0] - 2026-07-17

### Added
- Sprint 3.5: Event Bus Kafka + CloudEvents Integration
  - **Event publishing activities** for translation workflow milestones:
    - `publish_job_started_activity`: Emits `JOB_STARTED` event at workflow start
    - `publish_job_completed_activity`: Emits `JOB_COMPLETED` event on success
    - `publish_job_failed_activity`: Emits `JOB_FAILED` event on failure
    - `publish_step_completed_activity`: Emits `WORKFLOW_STEP_COMPLETED` after each stage
    - `publish_audiobook_generated_activity`: Emits `AUDIOBOOK_GENERATED` after Stage 6
  - **CloudEvents 1.0 specification** compliance via `cloudevents` library
    - Structured content mode with `application/cloudevents+json`
    - Required fields: id, source, type, specversion, datacontenttype, time
    - Optional: subject, traceparent, tracestate, correlationid
  - **Kafka producer integration** via `aiokafka`:
    - Async producer with singleton pattern per worker process
    - Topics: `pdftranslator.job.started`, `pdftranslator.job.completed`, `pdftranslator.job.failed`, `pdftranslator.workflow.step.completed`, `pdftranslator.audiobook.generated`
    - Configurable via `KAFKA_BOOTSTRAP_SERVERS` env var (default: localhost:9092)
    - Graceful shutdown via `shutdown_publisher()` activity
  - **Workflow integration** in `TranslationWorkflow` and `ResumeTranslationWorkflow`:
    - JOB_STARTED emitted at pipeline start
    - WORKFLOW_STEP_COMPLETED after each of 6 stages (detect, segment, translate, quality_check, store, generate_audio)
    - JOB_COMPLETED with stages_completed and duration_ms on success
    - JOB_FAILED with error and failed_stage on failure
    - AUDIOBOOK_GENERATED with audio_file_path and duration_ms when audio enabled
  - **Event data models**: `PublishEventInput`/`PublishEventOutput` dataclasses for activity I/O
  - **Shared events module** (`pdftranslator.shared.events`):
    - `EventPublisher` / `EventPublisherFactory` for Kafka producer management
    - `KafkaConfig` configuration dataclass
    - `EventTypes` / `EventSources` constants for CloudEvents type/source taxonomy
    - `create_event()` helper for CloudEvents construction with tracing headers

### CUPID
- **Composable**: Independent publish activities, reusable across workflows
- **Unix Philosophy**: Each activity does one thing (emit one event type)
- **Predictable**: Deterministic CloudEvents with structured schema, correlation IDs for tracing
- **Idiomatic**: Temporal activity patterns, async Kafka producer, dataclasses
- **Domain-Focused**: Events model translation job lifecycle milestones

## [v0.12.0] - 2026-07-17

### Added
- Sprint 3.4: Chaos Testing + Deterministic Replay
  - **Deterministic Replay Tests (3 tests)**: Verify workflow produces identical output for same input across replay runs
    - `test_translation_workflow_deterministic_output`: Full pipeline replay consistency
    - `test_workflow_replay_after_failure`: Resume from failure point
    - `test_resume_workflow_deterministic`: ResumeWorkflow deterministic behavior
  - **Activity Retry Behavior Tests (2 tests)**: Exception propagation and max retry handling
  - **Failure Mode Documentation (7 modes)**: Documented with description, recovery, retry policy
    - Activity timeout, transient error, permanent error
    - Workflow task timeout, Temporal server unavailable
    - Activity worker crash, non-deterministic code
  - **Chaos Engineering Experiments (3 tests)**:
    - `test_network_partition_simulation`: ConnectionError during activity
    - `test_worker_crash_simulation`: RuntimeError with replay recovery
    - `test_latency_injection_simulation`: High latency handling (100ms+)
  - **Mock temporalio in conftest.py**: Avoids Apple Silicon bus error

### CUPID
- Predictable: Deterministic replay verified across all pipeline stages
- Composable: Each test independent, reusable mock patterns
- Unix Philosophy: Single-responsibility tests, pure functions
- Idiomatic: pytest-asyncio, AsyncMock, parametrize patterns
- Domain-Focused: Tests mirror translation/embedding workflow chaos scenarios

## [v0.11.0] - 2026-07-16

### Added
- Sprint 3.3: Audio Generation Integration with Temporal Workflows
  - **Stage 6 added to TranslationWorkflow**: Audio generation from translated text
    - Optional audiobook generation controlled by `generate_audio` flag
    - Configurable: voice, format (m4a/mp3/wav/ogg/flac), sample_rate, bitrate
    - EBU R128 normalization via Rust audio service (auto-enabled)
    - Pluggable TTS engines (macOS Say, Piper, Coqui) via workflow parameter
  - **generate_audio_activity** calls Rust `pdftranslator-audio` via subprocess
    - Concatenates translated segments → stdin → audio binary → stdout → file
    - Returns audio file path, duration, format, size_bytes
  - **Workflow Input/Output updated**:
    - Input: `generate_audio`, `audio_voice`, `audio_format`, `audio_sample_rate`, `audio_bitrate`, `audio_normalize`, `audio_target_loudness`, `audio_engine`
    - Output: `audio_file_path`, `audio_duration_ms`
  - **Unit tests (14 total)** with mocked temporalio for Apple Silicon compatibility

### CUPID
- Composable: Activity independent, reusable, calls Rust via Unix pipeline
- Unix Philosophy: Stdin/stdout audio generation, single responsibility
- Predictable: Deterministic via explicit config, deterministic EBU R128
- Idiomatic: Python async subprocess, dataclasses, Temporal patterns
- Domain-Focused: Audiobook generation as natural Stage 6 of translation

## [v0.10.0] - 2026-07-16

### Added
- Sprint 3.2: Audio Service Rust Pipeline
  - **Pluggable TTS Engine Architecture**:
    - `TTSEngine` trait for composable backends (macOS Say, Piper, Coqui)
    - `MacOSSayEngine`: Native macOS `say` command integration with `afconvert` for format conversion
    - Voice listing, language detection, and configuration via `EngineConfig`
  - **Composable 5-Stage Pipeline** (Unix Philosophy):
    - `ChunkStage`: Sentence-aware text chunking with configurable size/overlap
    - `SynthesizeStage`: Parallel TTS synthesis with semaphore-controlled concurrency (default 4 workers)
    - `MergeStage`: ffmpeg-based audio concatenation with format preservation
    - `NormalizeStage`: **EBU R128 loudness normalization** via ffmpeg `loudnorm` (two-pass: measure → apply)
    - `EncodeStage`: Final format encoding (m4a/mp3/wav/ogg/flac) with configurable bitrate/sample rate
  - **EBU R128 Implementation**:
    - Two-pass loudnorm: measurement pass (JSON) + application pass with measured values
    - Target: -16 LUFS integrated, -1.5 dBTP true peak, 11 LU loudness range
    - True peak limiting and loudness range control
    - Tolerance-based skip (0.5 LUFS) to avoid unnecessary processing
  - **CLI: pdftranslator-audio** with commands:
    - `generate`: Text → audio (stdin/stdout pipeline support)
    - `voices`: List available voices per engine
    - `info`: Engine capability inspection
    - `validate`: Configuration validation
  - **Dependencies**: tokio, symphonia, ebur128, tempfile, clap, tracing, indicatif, async-trait

### CUPID
- Composable: `TTSEngine` trait enables pluggable backends; each pipeline stage is independently testable
- Unix Philosophy: Stdin/stdout pipeline, each stage does one thing (chunk/synthesize/merge/normalize/encode)
- Predictable: Deterministic EBU R128 normalization with explicit parameters, two-pass for accuracy
- Idiomatic: Rust traits, async/await, proper error handling with `anyhow`, typed configurations
- Domain-Focused: Models audiobook generation workflow end-to-end

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

