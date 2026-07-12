"""
TranslationJob Aggregate Root - Domain-Focused Rich Model.

CUPID Principle: Domain-Focused
- Encapsulates translation workflow state machine
- Enforces business invariants
- Behavior over data
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List
from uuid import UUID, uuid4
from enum import Enum

from .segment import Segment
from .glossary_ref import GlossaryReference
from ..repositories.exceptions import DomainError


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


@dataclass
class TranslationJob:
    """
    Aggregate root for translation workflow.

    Invariants:
    - Source and target languages must be valid ISO codes and differ
    - Status transitions follow state machine
    - Segments managed through aggregate
    - Glossary references validated
    """

    source_lang: str
    target_lang: str
    work_id: int
    volume_id: Optional[int] = None
    status: JobStatus = JobStatus.PENDING
    priority: JobPriority = JobPriority.NORMAL
    source_text: Optional[str] = None
    target_text: Optional[str] = None
    llm_provider: Optional[str] = None
    model_name: Optional[str] = None
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    id: Optional[int] = None
    uuid: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    _segments: List[Segment] = field(default_factory=list, repr=False)
    _glossary_refs: List[GlossaryReference] = field(default_factory=list, repr=False)

    def __post_init__(self) -> None:
        self._validate()

    def _validate(self) -> None:
        if not self.source_lang or len(self.source_lang) != 2:
            raise DomainError("Source language must be ISO 639-1 code (2 chars)")
        if not self.target_lang or len(self.target_lang) != 2:
            raise DomainError("Target language must be ISO 639-1 code (2 chars)")
        if self.source_lang == self.target_lang:
            raise DomainError("Source and target languages must differ")
        if self.work_id <= 0:
            raise DomainError("Work ID must be positive")

    @property
    def segments(self) -> tuple[Segment, ...]:
        return tuple(self._segments)

    @property
    def glossary_refs(self) -> tuple[GlossaryReference, ...]:
        return tuple(self._glossary_refs)

    @property
    def segment_count(self) -> int:
        return len(self._segments)

    @property
    def translated_segment_count(self) -> int:
        return sum(1 for s in self._segments if s.is_translated)

    @property
    def progress(self) -> float:
        if self.segment_count == 0:
            return 0.0
        return (self.translated_segment_count / self.segment_count) * 100

    @property
    def word_count_source(self) -> int:
        return sum(s.word_count_source for s in self._segments)

    @property
    def word_count_target(self) -> int:
        return sum(s.word_count_target for s in self._segments)

    # ----- State Machine Transitions -----

    def queue(self) -> None:
        self._transition_to(JobStatus.QUEUED, from_statuses=[JobStatus.PENDING])

    def start(self, llm_provider: str, model_name: str) -> None:
        self._transition_to(JobStatus.IN_PROGRESS, from_statuses=[JobStatus.QUEUED, JobStatus.PENDING])
        self.llm_provider = llm_provider
        self.model_name = model_name
        self.started_at = datetime.utcnow()

    def complete(self, target_text: str) -> None:
        if not target_text or not target_text.strip():
            raise DomainError("Cannot complete with empty target text")
        self._transition_to(JobStatus.COMPLETED, from_statuses=[JobStatus.IN_PROGRESS])
        self.target_text = target_text.strip()
        self.completed_at = datetime.utcnow()

    def fail(self, error: str) -> None:
        self._transition_to(JobStatus.FAILED, from_statuses=[JobStatus.IN_PROGRESS, JobStatus.QUEUED, JobStatus.PENDING])
        self.error_message = error
        self.completed_at = datetime.utcnow()

    def pause(self) -> None:
        self._transition_to(JobStatus.PAUSED, from_statuses=[JobStatus.IN_PROGRESS, JobStatus.QUEUED])

    def resume(self) -> None:
        self._transition_to(JobStatus.IN_PROGRESS, from_statuses=[JobStatus.PAUSED])

    def cancel(self) -> None:
        self._transition_to(JobStatus.CANCELLED, from_statuses=[JobStatus.PENDING, JobStatus.QUEUED, JobStatus.IN_PROGRESS, JobStatus.PAUSED])

    def _transition_to(self, new_status: JobStatus, from_statuses: List[JobStatus]) -> None:
        if self.status not in from_statuses:
            raise DomainError(f"Cannot transition from {self.status.value} to {new_status.value}")
        self.status = new_status
        self._touch()

    # ----- Segment Management -----

    def add_segment(self, segment: Segment) -> None:
        if segment.job_id is not None and segment.job_id != self.id:
            raise DomainError("Segment belongs to a different job")
        if any(s.segment_number == segment.segment_number for s in self._segments):
            raise DomainError(f"Segment {segment.segment_number} already exists")
        segment.job_id = self.id
        self._segments.append(segment)
        self._touch()

    def get_segment(self, segment_number: int) -> Optional[Segment]:
        return next((s for s in self._segments if s.segment_number == segment_number), None)

    # ----- Glossary References -----

    def add_glossary_ref(self, ref: GlossaryReference) -> None:
        if any(r.glossary_id == ref.glossary_id for r in self._glossary_refs):
            raise DomainError(f"Glossary {ref.glossary_id} already referenced")
        self._glossary_refs.append(ref)
        self._touch()

    def _touch(self) -> None:
        self.updated_at = datetime.utcnow()