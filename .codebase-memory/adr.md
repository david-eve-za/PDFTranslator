# ADR-003: Replace Loki + Grafana with ELK Stack (Elasticsearch, Logstash, Kibana)

## Status
Accepted

## Context
PDFTranslator currently uses Loki + Grafana for log aggregation and visualization. While Loki is a lightweight and cost-effective log aggregation system, the team has decided to migrate to the ELK Stack for the following reasons:

1. **Enterprise-grade features**: Elasticsearch provides full-text search, advanced analytics, and machine learning capabilities out of the box
2. **Ecosystem maturity**: ELK Stack has a larger ecosystem, more integrations, and better community support
3. **Kibana dashboards**: More powerful visualization and dashboarding capabilities compared to Grafana for log analysis
4. **Logstash pipeline**: Rich data processing capabilities (parsing, enrichment, filtering) before indexing
5. **Scalability**: Elasticsearch's distributed architecture scales better for high-volume logging
6. **Security**: Built-in security features (authentication, authorization, encryption) in Elastic Stack

## Decision
Replace the Loki + Grafana + Promtail stack with the ELK Stack:
- **Elasticsearch 8.x**: Log storage, indexing, and search engine
- **Logstash 8.x**: Log collection, parsing, enrichment, and forwarding
- **Kibana 8.x**: Visualization, dashboards, and log exploration UI

## Implementation Plan

### 1. Docker Compose Changes
- Remove: `loki`, `grafana`, `promtail` services
- Add: `elasticsearch`, `logstash`, `kibana` services
- Configure proper networking and volumes for persistence

### 2. Backend Logging Configuration (`logging_config.py`)
- Replace `LokiFormatter` with `ElasticsearchFormatter` (structured JSON for Elasticsearch)
- Replace `logging_loki.LokiHandler` with `elasticsearch-logger` or custom HTTP handler
- Maintain correlation ID propagation for distributed tracing
- Configure Logstash as the log shipper (recommended) or direct Elasticsearch ingestion

### 3. Backend Logs API (`routes/logs.py`)
- Replace Loki LogQL queries with Elasticsearch Query DSL
- Update `/logs/query` endpoint to use Elasticsearch search API
- Update `/logs/stream` endpoint for real-time log streaming (using Elasticsearch scroll or search_after)
- Update `/logs/labels` and `/logs/labels/{name}/values` for field discovery

### 4. Frontend Logs Viewer (`logs-viewer.component.ts`)
- Replace Loki query building with Elasticsearch query DSL
- Update response parsing from Loki format to Elasticsearch hits format
- Maintain same UI/UX for log filtering, pagination, and streaming

### 5. Configuration
- Replace `LOKI_URL` with `ELASTICSEARCH_URL` and `LOGSTASH_URL`
- Add Elasticsearch index template for structured logging
- Configure ILM (Index Lifecycle Management) for log retention

## Consequences

### Positive
- Full-text search across all log fields
- Advanced analytics (aggregations, machine learning jobs)
- Rich Kibana dashboards with Lens, Maps, Canvas
- Logstash pipelines for complex log processing
- Better multi-tenancy and RBAC support
- Industry-standard stack with extensive documentation

### Negative
- Higher resource consumption (Elasticsearch requires ~2-4GB RAM minimum)
- More complex deployment and tuning
- Elasticsearch licensing (SSPL/Elastic License) - consider OpenSearch as alternative
- Additional component (Logstash) to maintain
- Steeper learning curve for Query DSL vs LogQL

### Neutral
- Migration effort required for existing dashboards and queries
- Need to update monitoring/alerting rules

## Alternatives Considered

### Option 1: Keep Loki + Grafana (Status Quo)
- Pros: Lower resource usage, simpler, LogQL is intuitive
- Cons: Limited analytics, no ML, weaker visualization for logs

### Option 2: Migrate to OpenSearch + OpenSearch Dashboards
- Pros: Open source (Apache 2.0), AWS-backed, compatible with Elasticsearch API
- Cons: Smaller ecosystem, fewer integrations

### Option 3: Cloud-managed logging (Datadog, New Relic, etc.)
- Pros: Zero infrastructure management
- Cons: Cost, vendor lock-in, data egress

## Migration Steps
1. Create ADR (this document)
2. Update dependencies in `pyproject.toml`
3. Update `settings.py` with new config options
4. Rewrite `logging_config.py` for Elasticsearch
5. Update `docker-compose.yml` with ELK Stack services
6. Create Elasticsearch, Logstash, Kibana configurations
7. Update backend logs API routes
8. Update frontend logs viewer component
9. Update environment configuration and documentation
10. Test end-to-end logging pipeline
11. Create Kibana dashboards for PDFTranslator

## References
- Elastic Stack Documentation: https://www.elastic.co/guide/index.html
- Logstash Configuration: https://www.elastic.co/guide/en/logstash/current/configuration.html
- Kibana Dashboards: https://www.elastic.co/guide/en/kibana/current/dashboard.html
- Python Elasticsearch Client: https://elasticsearch-py.readthedocs.io/