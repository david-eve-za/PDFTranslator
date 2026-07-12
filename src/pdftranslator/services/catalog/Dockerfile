"""
Catalog Service Dockerfile.

CUPID Principle: Predictable
- Multi-stage build for small image
- Explicit dependencies
- Health checks included
"""

# Build stage
FROM python:3.11-slim as builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency files
COPY pyproject.toml ./

# Install dependencies
RUN pip install --no-cache-dir --prefix=/install \
    fastapi==0.109.* \
    uvicorn[standard]==0.27.* \
    pydantic==2.6.* \
    pydantic-settings==2.1.* \
    aiosqlite==0.19.* \
    python-multipart==0.0.* \
    pytest==8.0.* \
    pytest-asyncio==0.23.* \
    httpx==0.26.* \
    pact-python==1.6.*

# Runtime stage
FROM python:3.11-slim

WORKDIR /app

# Create non-root user
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Copy installed packages
COPY --from=builder /install /usr/local

# Copy application code
COPY src/pdftranslator/services/catalog/ ./src/pdftranslator/services/catalog/

# Create data directory
RUN mkdir -p /app/data && chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8001

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8001/health || exit 1

# Run application
CMD ["uvicorn", "pdftranslator.services.catalog.main:app", "--host", "0.0.0.0", "--port", "8001"]