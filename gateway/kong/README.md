# Kong API Gateway for PDFTranslator

## Overview

This directory contains the Kong API Gateway configuration for the PDFTranslator microservices architecture. Kong acts as the single entry point for all API traffic, providing:

- **Routing** - Path-based routing to microservices
- **Authentication** - API Key, JWT, OAuth2
- **Rate Limiting** - Per-service and global limits
- **Security** - CORS, IP restrictions, request size limits
- **Observability** - Prometheus metrics, request logging
- **Resilience** - Timeouts, retries, circuit breakers

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        CLIENTS                                    │
│  (Frontend, Mobile, Webhooks, CLI)                              │
└──────────────────────────┬──────────────────────────────────────┘
                           │ HTTPS
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                      KONG GATEWAY (Port 8000/8443)              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │  Routing    │  │  Auth       │  │  Rate Limit │             │
│  │  Plugins    │  │  Plugins    │  │  Plugins    │             │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘             │
└─────────┼────────────────┼────────────────┼────────────────────┘
          │                │                │
    ┌─────▼─────┐    ┌─────▼─────┐    ┌─────▼─────┐
    │ Catalog   │    │ Glossary  │    │Translation│
    │ Service   │    │ Service   │    │ Service   │
    │ :8001     │    │ :8002     │    │ :8003     │
    └───────────┘    └───────────┘    └───────────┘
```

## Quick Start

### Prerequisites

- Docker & Docker Compose v2+
- Upstream services running (or use mock services)

### 1. Configure Environment

```bash
cd gateway/kong
cp .env.example .env
# Edit .env with your configuration
```

### 2. Start Kong Stack

```bash
# Using startup script
./start-kong.sh start

# Or directly with docker-compose
docker-compose -f docker-compose.kong.yml up -d
```

### 3. Verify Startup

```bash
# Check Kong status
curl http://localhost:8001/status

# Test routing (requires upstream services)
curl http://localhost:8000/api/v1/catalog/works
curl http://localhost:8000/api/v1/glossaries
curl http://localhost:8000/api/v1/translation/jobs
```

### 4. Access Management UI

- **Konga Admin UI**: http://localhost:1337
- **Prometheus**: http://localhost:9090
- **Grafana**: http://localhost:3000 (admin/admin)

## Configuration

### Kong Declarative Config (`kong.yml`)

The declarative configuration defines all services, routes, and plugins:

```yaml
services:
  - name: catalog-service
    url: http://catalog-service:8001
    routes:
      - name: catalog-works
        paths:
          - /api/v1/catalog/works
    plugins:
      - name: rate-limiting
      - name: correlation-id
```

### Services & Routes

| Service | Upstream | Routes |
|---------|----------|--------|
| Catalog | `http://catalog-service:8001` | `/api/v1/catalog/works`, `/api/v1/catalog/volumes`, `/api/v1/catalog/chapters` |
| Glossary | `http://glossary-service:8002` | `/api/v1/glossaries`, `/api/v1/glossaries/build`, `/api/v1/glossaries/pipelines` |
| Translation | `http://translation-service:8003` | `/api/v1/translation/jobs`, `/api/v1/translation/pipelines` |
| Document | `http://document-service:8004` | `/api/v1/documents/extract` |
| Audio | `http://audio-service:8005` | `/api/v1/audio/generate`, `/api/v1/audio/voices` |

### Plugins Applied

| Plugin | Purpose | Configuration |
|--------|---------|---------------|
| `rate-limiting` | Throttle requests | Per-service limits (see `.env`) |
| `key-auth` | API Key authentication | Consumers: frontend, admin, webhook |
| `correlation-id` | Request tracing | Adds `X-Request-ID` header |
| `prometheus` | Metrics exposure | `/metrics` endpoint |
| `cors` | Cross-origin requests | Configured origins |
| `request-size-limiting` | Prevent large payloads | Service-specific limits |
| `response-transformer` | Security headers | CSP, X-Frame-Options, etc. |
| `ip-restriction` | Admin access control | Localhost only for admin |

## Rate Limits

Default limits (configured in `.env`):

| Service | Requests/min | Requests/hour |
|---------|--------------|---------------|
| Global | 1,000 | 50,000 |
| Catalog | 100 | 1,000 |
| Glossary | 60 | 500 |
| Translation | 30 | 200 |
| Document | 10 | 50 |
| Audio | 5 | 20 |

## Authentication

### API Keys

Three consumer types are pre-configured:

```bash
# Frontend application
curl -H "apikey: $FRONTEND_API_KEY" http://localhost:8000/api/v1/translation/jobs

# Admin access
curl -H "apikey: $ADMIN_API_KEY" http://localhost:8001/services

# Webhook receiver
curl -H "apikey: $WEBHOOK_API_KEY" http://localhost:8000/webhooks/...
```

### JWT (Production)

For production, enable JWT plugin:

```yaml
plugins:
  - name: jwt
    config:
      key_claim_name: kid
      claims_to_verify:
        - exp
```

## Development Mode

### Local Development (No Docker)

If running services locally without Docker:

1. Update `.env` with `host.docker.internal` URLs:
```bash
CATALOG_SERVICE_URL=http://host.docker.internal:8001
GLOSSARY_SERVICE_URL=http://host.docker.internal:8002
# ...
```

2. Or run Kong in DB-less mode with local config:
```bash
KONG_DATABASE=off
KONG_DECLARATIVE_CONFIG=/kong/kong.yml
```

### Hot Reload Config

```bash
# Apply config changes without restart
docker exec pdftranslator-kong kong config apply /kong/kong.yml

# Or via Admin API
curl -X POST http://localhost:8001/config -F "config=@kong.yml"
```

## Monitoring

### Prometheus Metrics

Kong exposes metrics at `http://localhost:8000/metrics`:

```bash
# Key metrics to monitor
curl http://localhost:8000/metrics | grep kong_http_status
curl http://localhost:8000/metrics | grep kong_latency
curl http://localhost:8000/metrics | grep kong_rate_limiting
```

### Grafana Dashboards

Pre-configured dashboard at `grafana/dashboards/kong-dashboard.json`:

- Requests per second by service/route
- Latency (P50, P95, P99)
- Error rates (4xx, 5xx)
- Rate limiting hits
- Connection pools
- Database/Redis health

### Alerting Rules

Example Prometheus alerts:

```yaml
groups:
  - name: kong-alerts
    rules:
      - alert: KongHighErrorRate
        expr: sum(rate(kong_http_status{code=~"5.."}[5m])) by (service) / sum(rate(kong_http_status[5m])) by (service) > 0.05
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "High 5xx error rate on {{ $labels.service }}"

      - alert: KongRateLimitExceeded
        expr: increase(kong_rate_limiting_latency_seconds_count[5m]) > 100
        for: 2m
        labels:
          severity: warning
        annotations:
          summary: "Rate limit exceeded for {{ $labels.service }}"
```

## Troubleshooting

### Common Issues

**Kong won't start**
```bash
# Check logs
docker logs pdftranslator-kong

# Check database connectivity
docker exec pdftranslator-kong kong migrations list

# Run migrations manually
docker exec pdftranslator-kong kong migrations bootstrap
```

**Routes not working**
```bash
# Check if routes are loaded
curl http://localhost:8001/routes | jq '.data[].paths[]'

# Check upstream connectivity
docker exec pdftranslator-kong curl -f http://catalog-service:8001/health
```

**Rate limiting too aggressive**
```bash
# Check rate limit metrics
curl http://localhost:8000/metrics | grep kong_rate_limiting

# Adjust in .env and restart
CATALOG_RATE_LIMIT_MINUTE=200 docker-compose restart kong
```

**SSL/Certificate issues**
```bash
# Generate self-signed for dev
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout certs/kong.key -out certs/kong.crt \
  -subj "/CN=localhost"

# Mount in docker-compose
volumes:
  - ./certs:/kong/certs:ro
```

## Production Checklist

- [ ] Use managed PostgreSQL (RDS, Cloud SQL)
- [ ] Enable SSL/TLS with valid certificates
- [ ] Configure Redis cluster for rate limiting
- [ ] Set up Kong clustering for HA
- [ ] Configure log aggregation (ELK, Datadog)
- [ ] Set up alerting on key metrics
- [ ] Implement API versioning strategy
- [ ] Configure WAF plugin for security
- [ ] Set up backup/restore procedures
- [ ] Load test with expected traffic

## File Structure

```
gateway/kong/
├── kong.yml                 # Declarative configuration
├── docker-compose.kong.yml  # Full stack with monitoring
├── start-kong.sh            # Startup script
├── .env.example             # Environment template
├── prometheus.yml           # Prometheus config
├── grafana/
│   ├── datasources.yml      # Prometheus datasource
│   ├── dashboards.yml       # Dashboard provisioning
│   └── dashboards/
│       └── kong-dashboard.json
└── README.md                # This file
```

## Upgrading Kong

```bash
# 1. Backup database
docker exec pdftranslator-kong-db pg_dump -U kong kong > backup.sql

# 2. Update image tag in docker-compose.kong.yml
#    image: kong:3.5  (or latest)

# 3. Run migrations
docker-compose -f docker-compose.kong.yml up -d kong-db
docker-compose -f docker-compose.kong.yml run --rm kong kong migrations up

# 4. Restart Kong
docker-compose -f docker-compose.kong.yml up -d kong
```

## References

- [Kong Documentation](https://docs.konghq.com/)
- [Kong Plugin Hub](https://docs.konghq.com/hub/)
- [Prometheus Metrics](https://docs.konghq.com/gateway/latest/monitoring/prometheus/)
- [Grafana Dashboards](https://grafana.com/grafana/dashboards/)