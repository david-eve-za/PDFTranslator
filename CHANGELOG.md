# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Work plan for CUPID microservices migration (docs/WORK_PLAN_CUPID.md)

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

