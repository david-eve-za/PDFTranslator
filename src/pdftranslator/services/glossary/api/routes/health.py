"""
Health Check Endpoints.

CUPID Principle: Predictable
- /health for liveness (service running)
- /ready for readiness (dependencies available)
"""

from __future__ import annotations
import logging
from dataclasses import dataclass
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException

from ...config import GlossarySettings
from ...infrastructure.database.connection import DatabaseConnection
from ...api.dependencies import get_database_connection

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/health", tags=["health"])


@dataclass
class HealthResponse:
    """Health check response."""
    status: str
    timestamp: str
    service: str
    version: str


@dataclass
class ReadinessResponse:
    """Readiness check response."""
    status: str
    timestamp: str
    database: str
    migrations: str


@router.get("")
async def health_check() -> HealthResponse:
    """
    Liveness probe - service is running.
    Returns 200 if process is alive.
    """
    return HealthResponse(
        status="healthy",
        timestamp=datetime.utcnow().isoformat() + "Z",
        service="glossary-service",
        version="1.0.0",
    )


@router.get("/ready")
async def readiness_check(
    db: DatabaseConnection = Depends(get_database_connection),
) -> ReadinessResponse:
    """
    Readiness probe - service can handle requests.
    Returns 200 if database is available and migrations applied.
    """
    db_status = "unknown"
    migrations_status = "unknown"

    try:
        # Test database connection
        async with db.connection() as conn:
            await conn.execute("SELECT 1")
            db_status = "connected"

        # Check migrations table
        async with db.connection() as conn:
            async with conn.execute("SELECT COUNT(*) FROM _migrations") as cur:
                row = await cur.fetchone()
                if row:
                    migrations_status = f"applied ({row[0]} migrations)"

    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        raise HTTPException(status_code=503, detail="Service not ready")

    overall_status = "ready" if db_status == "connected" else "not ready"

    return ReadinessResponse(
        status=overall_status,
        timestamp=datetime.utcnow().isoformat() + "Z",
        database=db_status,
        migrations=migrations_status,
    )