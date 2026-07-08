#!/usr/bin/env bash
# =============================================================================
# PDFTranslator — Start ELK Stack and Initialize
# =============================================================================
# Starts ELK services, waits for health, then runs initialization
# =============================================================================

set -euo pipefail

cd "$(dirname "$0")"

echo "=== Starting ELK Stack ==="
docker compose --profile logging up -d

echo ""
echo "=== Waiting for Elasticsearch ==="
until curl -s http://localhost:9200/_cluster/health?wait_for_status=yellow&timeout=5s >/dev/null; do
  printf "."
  sleep 2
done
echo ""
echo "Elasticsearch is ready"

echo ""
echo "=== Waiting for Kibana ==="
until curl -s http://localhost:5601/api/status >/dev/null; do
  printf "."
  sleep 3
done
echo ""
echo "Kibana is ready"

echo ""
echo "=== Running ELK Initialization ==="
./elk-init.sh

echo ""
echo "=== ELK Stack Ready ==="
echo "Elasticsearch: http://localhost:9200"
echo "Kibana:        http://localhost:5601"
echo "Logstash:      http://localhost:9600"
echo ""
echo "Next steps:"
echo "  1. Open Kibana at http://localhost:5601"
echo "  2. Go to Stack Management > Index Patterns"
echo "  3. Create index pattern: pdftranslator-logs*"
echo "  4. Time field: @timestamp"
echo "  5. Start exploring logs in Discover"