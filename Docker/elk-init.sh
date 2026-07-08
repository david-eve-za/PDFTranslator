#!/usr/bin/env bash
# =============================================================================
# PDFTranslator — ELK Stack Initialization Script
# =============================================================================
# Creates index templates, ILM policies, and component templates for log data
# Run once after Elasticsearch is healthy, or include in initialization workflow
# =============================================================================

set -euo pipefail

ELASTIC_URL="${ELASTIC_URL:-http://localhost:9200}"
ELASTIC_USER="${ELASTIC_USER:-elastic}"
ELASTIC_PASSWORD="${ELASTIC_PASSWORD:-}"

# Auth header
if [[ -n "$ELASTIC_PASSWORD" ]]; then
  AUTH="-u $ELASTIC_USER:$ELASTIC_PASSWORD"
else
  AUTH=""
fi

echo "=== Initializing Elasticsearch for PDFTranslator ==="
echo "Endpoint: $ELASTIC_URL"

# Wait for Elasticsearch to be ready
echo "Waiting for Elasticsearch..."
until curl -s $AUTH "$ELASTIC_URL/_cluster/health?wait_for_status=yellow&timeout=30s" >/dev/null; do
  sleep 2
done
echo "Elasticsearch is ready"

# =============================================================================
# 1. COMPONENT TEMPLATE: Base mappings for all log types
# =============================================================================
echo "Creating component template: pdftranslator-logs-base-mappings"
curl -s $AUTH -X PUT "$ELASTIC_URL/_component_template/pdftranslator-logs-base-mappings" \
  -H "Content-Type: application/json" \
  -d '{
  "template": {
    "mappings": {
      "dynamic_templates": [
        {
          "strings_as_keyword": {
            "match_mapping_type": "string",
            "mapping": {
              "type": "keyword",
              "ignore_above": 1024
            }
          }
        }
      ],
      "properties": {
        "@timestamp": { "type": "date", "format": "strict_date_optional_time||epoch_millis" },
        "level": { "type": "keyword" },
        "logger": { "type": "keyword" },
        "service": { "type": "keyword" },
        "correlation_id": { "type": "keyword" },
        "message": { "type": "text", "analyzer": "standard" },
        "container_name": { "type": "keyword" },
        "container_id": { "type": "keyword" },
        "image_name": { "type": "keyword" },
        "tags": { "type": "keyword" },
        "clientip": { "type": "ip" },
        "auth": { "type": "keyword" },
        "verb": { "type": "keyword" },
        "request": { "type": "keyword" },
        "httpversion": { "type": "keyword" },
        "response": { "type": "integer" },
        "bytes": { "type": "long" },
        "referrer": { "type": "keyword" },
        "agent": { "type": "keyword" },
        "type": { "type": "keyword" },
        "component": { "type": "keyword" }
      }
    }
  }
}' || echo "Component template may already exist"

# =============================================================================
# 2. COMPONENT TEMPLATE: Index settings (shards, replicas, codec)
# =============================================================================
echo "Creating component template: pdftranslator-logs-settings"
curl -s $AUTH -X PUT "$ELASTIC_URL/_component_template/pdftranslator-logs-settings" \
  -H "Content-Type: application/json" \
  -d '{
  "template": {
    "settings": {
      "index.number_of_shards": 1,
      "index.number_of_replicas": 0,
      "index.codec": "best_compression",
      "index.refresh_interval": "5s",
      "index.lifecycle.name": "pdftranslator-logs",
      "index.lifecycle.rollover_alias": "pdftranslator-logs"
    }
  }
}' || echo "Component template may already exist"

# =============================================================================
# 3. INDEX TEMPLATE: Combines component templates for data stream
# =============================================================================
echo "Creating index template: pdftranslator-logs"
curl -s $AUTH -X PUT "$ELASTIC_URL/_index_template/pdftranslator-logs" \
  -H "Content-Type: application/json" \
  -d '{
  "index_patterns": ["pdftranslator-logs*"],
  "composed_of": ["pdftranslator-logs-base-mappings", "pdftranslator-logs-settings"],
  "priority": 100,
  "data_stream": {},
  "version": 1
}' || echo "Index template may already exist"

# =============================================================================
# 4. ILM POLICY: Hot-Warm-Cold-Delete lifecycle
# =============================================================================
echo "Creating ILM policy: pdftranslator-logs"
curl -s $AUTH -X PUT "$ELASTIC_URL/_ilm/policy/pdftranslator-logs" \
  -H "Content-Type: application/json" \
  -d '{
  "policy": {
    "phases": {
      "hot": {
        "min_age": "0ms",
        "actions": {
          "rollover": {
            "max_size": "1gb",
            "max_age": "1d",
            "max_docs": 10000000
          },
          "set_priority": { "priority": 100 }
        }
      },
      "warm": {
        "min_age": "7d",
        "actions": {
          "readonly": {},
          "forcemerge": { "max_num_segments": 1 },
          "shrink": { "number_of_shards": 1 },
          "set_priority": { "priority": 50 }
        }
      },
      "cold": {
        "min_age": "30d",
        "actions": {
          "set_priority": { "priority": 0 }
        }
      },
      "delete": {
        "min_age": "90d",
        "actions": {
          "delete": { "delete_searchable_snapshot": true }
        }
      }
    }
  }
}' || echo "ILM policy may already exist"

# =============================================================================
# 5. BOOTSTRAP DATA STREAM (creates first backing index)
# =============================================================================
echo "Bootstrapping data stream: pdftranslator-logs"
curl -s $AUTH -X PUT "$ELASTIC_URL/_data_stream/pdftranslator-logs" \
  -H "Content-Type: application/json" \
  -d '{}' || echo "Data stream may already exist"

# =============================================================================
# 6. KIBANA INDEX PATTERN (requires Kibana running)
# =============================================================================
if curl -s -f "http://localhost:5601/api/status" >/dev/null 2>&1; then
  echo "Kibana detected, creating index pattern..."
  sleep 5
  curl -s -X POST "http://localhost:5601/api/saved_objects/index-pattern/pdftranslator-logs" \
    -H "Content-Type: application/json" \
    -H "kbn-xsrf: true" \
    -d '{
      "attributes": {
        "title": "pdftranslator-logs*",
        "timeFieldName": "@timestamp"
      }
    }' || echo "Index pattern may already exist"
else
  echo "Kibana not yet available, skipping index pattern creation"
  echo "Run manually after Kibana starts:"
  echo "  curl -X POST http://localhost:5601/api/saved_objects/index-pattern/pdftranslator-logs \\"
  echo "    -H 'Content-Type: application/json' -H 'kbn-xsrf: true' \\"
  echo "    -d '{\"attributes\":{\"title\":\"pdftranslator-logs*\",\"timeFieldName\":\"@timestamp\"}}'"
fi

echo ""
echo "=== Elasticsearch initialization complete ==="
echo ""
echo "Verify:"
echo "  curl $AUTH $ELASTIC_URL/_cat/indices?v"
echo "  curl $AUTH $ELASTIC_URL/_cat/data_streams?v"
echo "  curl $AUTH $ELASTIC_URL/_ilm/policy/pdftranslator-logs?pretty"
echo ""
echo "Kibana: http://localhost:5601"
echo "  Stack Management > Index Patterns > Create: pdftranslator-logs*"