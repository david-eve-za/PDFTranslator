# Changelog - Sprint 2.1: Glossary Pipeline HTTP Service

## Summary
Implemented the Glossary Pipeline HTTP Service as part of Sprint 2.1 (Phase 2: Unix Pipeline Replacement) of the CUPID Microservices Migration.

## Changes

### New Files Created

#### Domain Layer
- `src/pdftranslator/services/glossary/domain/models/generators.py` - Entity generators with ID/counter
- `src/pdftranslator/services/glossary/domain/services/commands.py` - Command objects for all operations
- `src/pdftranslator/services/glossary/domain/services/glossary_service.py` - Domain service coordinating pipeline

#### API Layer
- `src/pdftranslator/services/glossary/api/schemas/__init__.py` - Pydantic v2 request/response models
- `src/pdftranslator/services/glossary/api/routes/glossary.py` - REST endpoints for CRUD + pipeline stages
- `src/pdftranslator/services/glossary/api/routes/health.py` - /health and /health/ready endpoints
- `src/pdftranslator/services/glossary/api/dependencies.py` - FastAPI dependency injection

#### Infrastructure Layer
- `src/pdftranslator/services/glossary/infrastructure/database/connection.py` - Async SQLite with aiosqlite
- `src/pdftranslator/services/glossary/infrastructure/database/migrations.py` - Versioned migrations (001, 002)
- `src/pdftranslator/services/glossary/infrastructure/database/repositories.py` - SQLite repository implementations

#### Application Entry Points
- `src/pdftranslator/services/glossary/main.py` - FastAPI app with lifespan, middleware
- `src/pdftranslator/services/glossary/run.py` - CLI runner for migrate/serve commands
- `src/pdftranslator/services/glossary/config/settings.py` - Pydantic Settings with env vars

#### Tests
- `tests/services/glossary/test_domain_models.py` - Unit tests for domain models
- `tests/services/glossary/test_service.py` - Unit tests for glossary service
- `tests/services/glossary/test_integration.py` - Integration tests for full pipeline
- `tests/services/glossary/test_contract.py` - Pact contract tests for API
- `tests/services/glossary/conftest.py` - Test fixtures

### Architecture Decisions

1. **CUPID Principles Applied:**
   - **Composable**: Each pipeline stage is independently testable as HTTP endpoint
   - **Unix Philosophy**: Each stage does one thing (extract, filter, validate, embed, translate, store)
   - **Predictable**: Explicit state machine for pipeline, Pydantic validation
   - **Idiomatic**: FastAPI + Pydantic v2, async/await, dependency injection
   - **Domain-Focused**: Domain layer has zero infrastructure dependencies

2. **Clean Architecture:**
   - Domain layer: Pure Python, no external deps
   - Infrastructure: SQLite implementations behind protocols
   - API: FastAPI routes using dependency injection

3. **Pipeline Stages (6 HTTP Endpoints):**
   - POST `/api/v1/glossaries/pipelines/stages/extract` - NLTK NER + patterns
   - POST `/api/v1/glossaries/pipelines/stages/filter` - Deduplication
   - POST `/api/v1/glossaries/pipelines/stages/validate` - LLM validation
   - POST `/api/v1/glossaries/pipelines/stages/embed` - Vector embeddings
   - POST `/api/v1/glossaries/pipelines/stages/translate` - LLM translation
   - POST `/api/v1/glossaries/pipelines/stages/store` - Persist to DB

### Database Schema (Migration 001)

- `works` - Work metadata
- `volumes` - Volume-level data with glossary build status
- `chapters` - Chapter text storage
- `glossaries` - Glossary per work/language pair
- `glossary_entries` - Terms with translation, entity type, verification
- `build_pipelines` - Pipeline execution state
- `pipeline_stages` - Per-stage execution tracking
- `entity_blacklist` - Stopwords/metadata terms to exclude
- `fantasy_terms` - Pre-seeded fantasy vocabulary
- `entity_candidates` - Extracted entities during build

### Configuration

```bash
# Required
GLOSSARY_DATABASE_PATH=data/glossary.db
NVIDIA_API_KEY=<nim_key>

# Optional
GLOSSARY_HOST=0.0.0.0
GLOSSARY_PORT=8003
GLOSSARY_LOG_LEVEL=INFO
GLOSSARY_DOCS_URL=/docs
```

### Running the Service

```bash
# Run migrations
python -m src.pdftranslator.services.glossary.run migrate

# Start service
python -m src.pdftranslator.services.glossary.run serve
# or
uvicorn src.pdftranslator.services.glossary.main:app --port 8003
```

### API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /health | Liveness probe |
| GET | /health/ready | Readiness probe |
| POST | /api/v1/glossaries | Create glossary |
| GET | /api/v1/glossaries | List glossaries |
| GET | /api/v1/glossaries/work/{work_id} | Get glossary by work |
| GET | /api/v1/glossaries/{id}/search | Search terms |
| POST | /api/v1/glossaries/build | Full pipeline |
| GET | /api/v1/glossaries/pipelines | List pipelines |
| GET | /api/v1/glossaries/pipelines/{work}/{volume} | Pipeline status |
| POST | /api/v1/glossaries/pipelines/stages/extract | Stage 1: Extract |
| POST | /api/v1/glossaries/pipelines/stages/filter | Stage 2: Filter |
| POST | /api/v1/glossaries/pipelines/stages/validate | Stage 3: Validate |
| POST | /api/v1/glossaries/pipelines/stages/embed | Stage 4: Embed |
| POST | /api/v1/glossaries/pipelines/stages/translate | Stage 5: Translate |
| POST | /api/v1/glossaries/pipelines/stages/store | Stage 6: Store |

### Testing

```bash
# Unit tests
pytest tests/services/glossary/test_domain_models.py -v
pytest tests/services/glossary/test_service.py -v

# Integration tests
pytest tests/services/glossary/test_integration.py -v

# Contract tests
pytest tests/services/glossary/test_contract.py -v
```

## Next Steps (Sprint 2.2)

1. Wire up real LLM integration (NVIDIA NIM) for validation/translation stages
2. Add embedding generation with nvidia/nv-embedqa-e5-v5
3. Implement entity blacklist/fantasy terms filtering
4. Add contract testing with Pact for Angular frontend compatibility
5. Set up CI/CD pipeline for glossary service