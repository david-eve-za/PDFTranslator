#!/bin/bash
# Kong Gateway Startup Script for PDFTranslator

set -euo pipefail

KONG_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMPOSE_FILE="$KONG_DIR/docker-compose.kong.yml"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Check Docker
check_docker() {
    if ! command -v docker &> /dev/null; then
        log_error "Docker not found. Please install Docker first."
        exit 1
    fi
    if ! docker info &> /dev/null; then
        log_error "Docker daemon not running. Start Docker first."
        exit 1
    fi
}

# Check required ports
check_ports() {
    local ports=(8000 8001 8443 8444 1337 9090 3000)
    for port in "${ports[@]}"; do
        if lsof -i ":$port" >/dev/null 2>&1; then
            log_warn "Port $port is in use. Kong may fail to start."
        fi
    done
}

# Start Kong stack
start_kong() {
    log_info "Starting Kong API Gateway stack..."
    cd "$KONG_DIR"
    docker compose -f "$COMPOSE_FILE" up -d
}

# Wait for Kong to be healthy
wait_for_kong() {
    log_info "Waiting for Kong to be ready..."
    local retries=30
    local count=0

    while [ $count -lt $retries ]; do
        if curl -s -f http://localhost:8001/status >/dev/null 2>&1; then
            log_info "Kong is ready!"
            return 0
        fi
        sleep 2
        count=$((count + 1))
    done

    log_error "Kong failed to start within timeout"
    docker compose -f "$COMPOSE_FILE" logs kong
    exit 1
}

# Apply declarative config (for DB-less mode fallback)
apply_config() {
    log_info "Applying declarative configuration..."
    if docker compose -f "$COMPOSE_FILE" exec -T kong kong config apply /kong/kong.yml 2>/dev/null; then
        log_info "Declarative config applied"
    else
        log_warn "Failed to apply declarative config (may already be in DB mode)"
    fi
}

# Show status
show_status() {
    echo ""
    echo "=============================================="
    echo "  Kong Gateway URLs"
    echo "=============================================="
    echo "  Proxy (API):      http://localhost:8000"
    echo "  Proxy (HTTPS):    https://localhost:8443"
    echo "  Admin API:        http://localhost:8001"
    echo "  Konga UI:         http://localhost:1337"
    echo "  Prometheus:       http://localhost:9090"
    echo "  Grafana:          http://localhost:3000 (admin/admin)"
    echo ""
    echo "  Test API endpoints:"
    echo "    curl http://localhost:8000/api/v1/catalog/works"
    echo "    curl http://localhost:8000/api/v1/glossaries"
    echo "    curl http://localhost:8000/api/v1/translation/jobs"
    echo ""
}

# Stop Kong
stop_kong() {
    log_info "Stopping Kong stack..."
    cd "$KONG_DIR"
    docker compose -f "$COMPOSE_FILE" down
}

# Show logs
logs_kong() {
    cd "$KONG_DIR"
    docker compose -f "$COMPOSE_FILE" logs -f kong
}

# Main
main() {
    case "${1:-start}" in
        start)
            check_docker
            check_ports
            start_kong
            wait_for_kong
            apply_config
            show_status
            ;;
        stop)
            stop_kong
            ;;
        restart)
            stop_kong
            sleep 2
            main start
            ;;
        logs)
            logs_kong
            ;;
        status)
            show_status
            ;;
        *)
            echo "Usage: $0 {start|stop|restart|logs|status}"
            exit 1
            ;;
    esac
}

main "$@"