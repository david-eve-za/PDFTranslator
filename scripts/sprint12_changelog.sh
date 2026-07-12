#!/bin/bash
# Generate CHANGELOG entry for Sprint 1.2

cat >> CHANGELOG.md << 'EOF'

## [v0.2.0] - 2026-07-12

### Added
- Catalog Service as independent microservice (CUPID Composable, Domain-Focused)
- Rich domain models: Work (aggregate root), Volume, Chapter with business invariants
- Repository protocols (WorkRepository, VolumeRepository, ChapterRepository) for Composable dependency injection
- SQLite implementations with Unit of Work pattern for Predictable transactions
- REST API endpoints:
  - GET/POST/PUT/DELETE /works
  - GET/POST /works/{work_id}/volumes
  - GET /works/{work_id}/volumes/{volume_id}
  - GET /volumes/{volume_id}/chapters
  - GET /volumes/{volume_id}/chapters/{chapter_id}
- Pydantic API schemas with validation (separate from domain models)
- Pact contract tests for Angular frontend compatibility
- Comprehensive unit tests for domain models (invariants, behavior)
- OpenAPI documentation at /docs
- Health checks at /health and /ready
- Dockerfile for containerized deployment
- Database migrations with explicit schema, constraints, and indexes

### Changed
- Separated Catalog domain from monolithic codebase
- Database schema now in catalog service (works, volumes, chapters tables)
- API contracts versioned and documented

### Architecture
- CUPID Compliance: 5/5 principles satisfied
  - Composable: Protocol-based DI, gRPC-ready protocols
  - Unix Philosophy: Single-responsibility service, stateless HTTP
  - Predictable: ACID transactions, explicit errors, versioned contracts
  - Idiomatic: FastAPI, Pydantic, async/await, type hints
  - Domain-Focused: Rich aggregates with invariants, no anemic models

EOF