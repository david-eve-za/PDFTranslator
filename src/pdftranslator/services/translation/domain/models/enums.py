"""
Translation Domain Enums - Separated to break circular import.

CUPID Principle: Domain-Focused - Pure enums with no infrastructure dependencies.
"""

from __future__ import annotations
from enum import Enum


class JobStatus(str, Enum):
    """Translation job status state machine."""
    PENDING = "pending"
    QUEUED = "queued"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"
    CANCELLED = "cancelled"


class JobPriority(int, Enum):
    """Job priority levels."""
    LOW = 0
    NORMAL = 50
    HIGH = 100
    URGENT = 200