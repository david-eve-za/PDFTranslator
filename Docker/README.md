# PDFTranslator Docker

All Docker-related files for PDFTranslator consolidated in one place.

## Structure

```
docker/
├── docker-compose.yml          # Unified compose (main app + ELK logging stack)
├── Dockerfile.backend          # Backend multi-stage build
├── Dockerfile.frontend         # Frontend multi-stage build
├── nginx.conf                  # Nginx reverse proxy config
├── logstash/
│   ├── logstash.conf           # Logstash pipeline configuration
│   └── patterns/
│       └── pdftranslator       # Custom Grok patterns
├── filebeat/
│   └── filebeat.yml            # Filebeat configuration
├── init/
│   └── 001_schema.sql          # Complete PostgreSQL schema
├── elk-init.sh                 # ELK Stack initialization script
├── start-elk.sh                # Start ELK + initialize
├── env.example                 # Environment variables template
└── README.md                   # This file
```

## Quick Start

### 1. Prerequisites
- Docker 24+ and Docker Compose 2.20+
- `.env` file with required secrets (see below)
- **Minimum 4GB RAM** recommended for ELK Stack (Elasticsearch heap: 1GB)

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
- **Elasticsearch** (port 9200) - Search & analytics engine
- **Logstash** (port 5044/9600) - Log processing pipeline
- **Filebeat** - Lightweight log shipper (Docker autodiscover)
- **Kibana** (port 5601) - Visualization & dashboards
- **Backend API** (port 8000) - FastAPI + structured logging
- **Frontend** (port 80) - Angular via Nginx
- **CloudBeaver** (port 8978) - Database web UI

### 4. Development Mode (Hot Reload)
```bash
# From docker directory
docker compose --profile dev up -d
```
This adds:
- **Backend Dev** (port 8000) - Hot reload via `uvicorn --reload`
- **Frontend Dev** (port 4200) - `ng serve` with file watching

### 5. Start Only ELK Stack (Logging)
```bash
# Quick start script (starts ELK + runs initialization)
./start-elk.sh

# Or manually:
docker compose --profile logging up -d
./elk-init.sh
```

## Access Points

| Service | URL | Credentials |
|---------|-----|-------------|
| Frontend App | http://localhost | - |
| Backend API | http://localhost:8000 | - |
| API Docs | http://localhost:8000/docs | - |
| Kibana | http://localhost:5601 | - |
| Elasticsearch | http://localhost:9200 | - |
| CloudBeaver | http://localhost:8978 | - |

## Key Features

### Unified Logging (ELK Stack)
- **Filebeat** autodiscovers Docker containers with `com.docker.compose.project=pdftranslator` label
- **Logstash** parses JSON logs, extracts `correlation_id`, `level`, `logger`, `service`
- **Nginx** access/error logs parsed via Grok patterns
- **Elasticsearch** stores logs in data stream `pdftranslator-logs*` with ILM (90-day retention)
- **Kibana** for searching, dashboards, and alerting

### Query Examples (KQL in Kibana Discover)
```kql
# Backend errors
level:ERROR and service:backend

# Traced requests
correlation_id:*

# Translation failures
service:backend and message:"translation failed"

# Slow translation chapters
service:backend and duration_ms:>5000

# Nginx 5xx errors
service:nginx and response:[500 TO 599]
```

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

# Start only ELK stack
docker compose --profile logging up -d

# Initialize ELK (index templates, ILM, data stream)
./elk-init.sh

# View logs
docker compose logs -f backend
docker compose logs -f logstash
docker compose logs -f filebeat

# Stop and remove volumes (clean slate)
docker compose down -v

# Rebuild specific service
docker compose build --no-cache backend

# Access DB
docker exec -it pdftranslator_db psql -U translator_user -d book_translator

# Check Elasticsearch health
curl http://localhost:9200/_cluster/health?pretty

# Check data stream
curl http://localhost:9200/_cat/data_streams?v

# View ILM policy
curl http://localhost:9200/_ilm/policy/pdftranslator-logs?pretty
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
ELASTIC_HEAP_SIZE=1g
LOGSTASH_HEAP_SIZE=512m
KIBANA_HEAP_SIZE=512m
LOG_LEVEL=INFO
```

## Notes

- **Network**: All services on `translator_net` (subnet 172.29.0.0/16)
- **Volumes**: Named volumes persist data across restarts
- **Healthchecks**: All critical services have readiness probes
- **Resources**: Memory limits/reservations configured per service
- **Security**: Non-root user in backend container, immutable nginx assets

## Migration from Loki/Grafana

If upgrading from the old Loki + Grafana stack:
```bash
# 1. Stop old stack
docker compose down -v  # This removes loki_data, grafana_data volumes

# 2. Remove old config files (already done in this version)
# rm loki-config.yaml promtail-config.yaml
# rm -rf grafana/

# 3. Update .env with new variables (ELASTIC_HEAP_SIZE, etc.)
# 4. Start new stack
docker compose --profile prod up -d
./elk-init.sh
```