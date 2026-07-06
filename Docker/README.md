# PDFTranslator Docker

All Docker-related files for PDFTranslator consolidated in one place.

## Structure

```
docker/
├── docker-compose.yml          # Unified compose (main app + logging stack)
├── Dockerfile.backend          # Backend multi-stage build
├── Dockerfile.frontend         # Frontend multi-stage build
├── nginx.conf                  # Nginx reverse proxy config
├── loki-config.yaml            # Loki 3.x single-process config
├── promtail-config.yaml        # Promtail log shipper config
├── init/
│   └── 001_schema.sql          # Complete PostgreSQL schema
├── grafana/
│   ├── provisioning/
│   │   ├── datasources/        # Auto-provision Loki datasource
│   │   └── dashboards/         # Auto-load dashboards
│   └── dashboards/
│       └── pdftranslator-logs.json  # Pre-built log dashboard
├── env.example                 # Environment variables template
└── README.md                   # This file
```

## Quick Start

### 1. Prerequisites
- Docker 24+ and Docker Compose 2.20+
- `.env` file with required secrets (see below)

### 2. Configuration
```bash
# From project root
cd docker
cp env.example .env
# Edit .env with your credentials:
# - POSTGRES_PASSWORD (required)
# - NVIDIA_API_KEY (for NVIDIA LLM)
# - GOOGLE_API_KEY (for Gemini LLM)
```

### 3. Start All Services (Production)
```bash
# From docker directory
docker compose --profile prod up -d
```

This starts:
- **PostgreSQL + pgvector** (port 5432)
- **Loki** (port 3100) - Log aggregation
- **Grafana** (port 3000) - Log visualization (admin/admin)
- **Promtail** - Ships container logs to Loki
- **Backend API** (port 8000) - FastAPI + Loki logging
- **Frontend** (port 80) - Angular via Nginx

### 4. Development Mode (Hot Reload)
```bash
# From docker directory
docker compose --profile dev up -d
```
This adds:
- **Backend Dev** (port 8000) - Hot reload via `uvicorn --reload`
- **Frontend Dev** (port 4200) - `ng serve` with file watching

## Access Points

| Service | URL | Credentials |
|---------|-----|-------------|
| Frontend App | http://localhost | - |
| Backend API | http://localhost:8000 | - |
| API Docs | http://localhost:8000/docs | - |
| Grafana | http://localhost:3000 | admin / admin |
| Loki | http://localhost:3100/ready | - |

## Key Features

### Unified Logging (Loki + Grafana)
- All backend logs → Loki via `logging_loki` handler
- Structured JSON logs with `correlation_id`
- Pre-built dashboard at `grafana/dashboards/pdftranslator-logs.json`
- Promtail ships Docker container logs automatically

### Database Initialization
Schema auto-applied on first DB start via `init/001_schema.sql` (includes pgvector, all tables, indexes, triggers).

### Multi-Stage Builds
- **Backend**: Builder installs deps + pre-caches NLTK/KeyBERT models → Runtime copies only needed artifacts
- **Frontend**: Node build → Nginx serve with SPA routing + API proxy + SSE support

## Commands

```bash
# Start production stack
docker compose --profile prod up -d

# Start dev stack (hot reload)
docker compose --profile dev up -d

# View logs
docker compose logs -f backend
docker compose logs -f loki

# Stop and remove volumes (clean slate)
docker compose down -v

# Rebuild specific service
docker compose build --no-cache backend

# Access DB
docker exec -it pdftranslator_db psql -U translator_user -d book_translator
```

## Environment Variables

Required in `.env`:
```bash
POSTGRES_PASSWORD=your_secure_password
NVIDIA_API_KEY=your_nvidia_key      # For NVIDIA LLM backend
GOOGLE_API_KEY=your_google_key      # For Gemini backend
```

Optional overrides:
```bash
POSTGRES_USER=translator_user
POSTGRES_DB=book_translator
POSTGRES_PORT=5432
APP_PORT=80
NLP_USE_KEYBERT=true
```

## Notes

- **Network**: All services on `translator_net` (subnet 172.29.0.0/16)
- **Volumes**: Named volumes persist data across restarts
- **Healthchecks**: All critical services have readiness probes
- **Resources**: Memory limits/reservations configured per service
- **Security**: Non-root user in backend container, immutable nginx assets

## Deprecated
- Root-level `docker-compose.yml` - Use `docker/docker-compose.yml`