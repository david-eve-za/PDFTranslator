# PDFTranslator Catalog Service

Independent microservice for managing Works, Volumes, and Chapters.

## Overview

This service implements the **Catalog** domain as a standalone microservice following **CUPID principles**:

- **Composable**: Protocol-based dependency injection, swappable implementations
- **Unix Philosophy**: Single responsibility - Catalog API only
- **Predictable**: ACID transactions, explicit errors, versioned OpenAPI contracts
- **Idiomatic**: FastAPI, Pydantic, async/await, type hints throughout
- **Domain-Focused**: Rich aggregates with invariants, no anemic models

## Architecture

```
src/pdftranslator/services/catalog/
├── api/                    # HTTP layer
│   ├── routes/             # FastAPI routers (works, volumes, chapters)
│   ├── schemas/            # Pydantic request/response models
│   └── dependencies.py     # DI container
├── domain/                 # Business logic (no infrastructure)
│   ├── models/             # Rich domain models (Work, Volume, Chapter)
│   ├── repositories/       # Repository protocols (interfaces)
│   └── services/           # Domain services (CatalogService)
├── infrastructure/         # External concerns
│   └── database/           # SQLite implementations
├── config/                 # Settings (Pydantic BaseSettings)
├── main.py                 # FastAPI app factory
└── tests/                  # Unit + Contract tests
```

## Quick Start

### Local Development

```bash
cd src/pdftranslator/services/catalog
pip install -e ".[dev]"

# Run migrations
sqlite3 data/catalog.db < infrastructure/database/migrations/001_catalog_schema.sql

# Start server
uvicorn pdftranslator.services.catalog.main:app --reload --port 8001
```

### Docker

```bash
docker build -t pdftranslator-catalog .
docker run -p 8001:8001 -v $(pwd)/data:/app/data pdftranslator-catalog
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | /works | List works (paginated) |
| POST | /works | Create work |
| GET | /works/{id} | Get work with volumes |
| GET | /works/uuid/{uuid} | Get work by UUID |
| PUT | /works/{id} | Update work metadata |
| DELETE | /works/{id} | Delete work (cascades) |
| GET | /works/{work_id}/volumes | List volumes for work |
| GET | /works/{work_id}/volumes/{id} | Get volume with chapters |
| POST | /works/{work_id}/volumes | Create volume |
| GET | /volumes/{volume_id}/chapters | List chapters (paginated) |
| GET | /volumes/{volume_id}/chapters/{id} | Get chapter |

## Health Checks

- `GET /health` - Liveness probe
- `GET /ready` - Readiness probe (checks DB)

## Documentation

- Swagger UI: `http://localhost:8001/docs`
- ReDoc: `http://localhost:8001/redoc`
- OpenAPI JSON: `http://localhost:8001/openapi.json`

## Configuration

Environment variables (prefix `CATALOG_`):

| Variable | Default | Description |
|----------|---------|-------------|
| CATALOG_DATABASE_PATH | data/catalog.db | SQLite database path |
| CATALOG_HOST | 0.0.0.0 | Bind host |
| CATALOG_PORT | 8001 | Bind port |
| CATALOG_CORS_ORIGINS | ["http://localhost:5173", "http://localhost:3000"] | Allowed origins |
| CATALOG_LOG_LEVEL | INFO | Log level |

## Testing

```bash
# Unit tests
pytest tests/unit -v

# Contract tests (Pact)
pytest tests/contract -v
```

## Domain Model

### Work (Aggregate Root)
- Invariants: Non-empty title, valid ISO 639-1 languages, source ≠ target
- Behavior: Manages volumes, calculates translation progress

### Volume (Entity)
- Invariants: Positive volume number, belongs to work
- Behavior: Manages chapters, tracks glossary build status

### Chapter (Entity)
- Invariants: Positive chapter number (if set)
- Behavior: Manages original/translated text, translation state

## Contract Testing

Pact contracts ensure Angular frontend compatibility:

```bash
# Generate pacts
pytest tests/contract/test_catalog_pact.py

# Verify against provider
pact-verifier --provider-base-url http://localhost:8001 --pact-dir ./pacts
```

## CUPID Compliance Checklist

- [x] **Composable**: Repository protocols, DI, no concrete deps in domain
- [x] **Unix Philosophy**: Single service, stateless HTTP, JSON I/O
- [x] **Predictable**: UoW transactions, explicit errors, OpenAPI contracts
- [x] **Idiomatic**: FastAPI patterns, type hints, async throughout
- [x] **Domain-Focused**: Rich aggregates, behavior over data, invariants