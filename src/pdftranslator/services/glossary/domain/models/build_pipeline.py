"""
Build Pipeline - Multi-stage glossary construction workflow.

CUPID Principle: Unix Philosophy
- Each stage is an independent, composable unit
- Stages communicate via explicit data contracts
- Pipeline orchestrates, stages execute
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any
import uuid


class PipelineStageStatus(Enum):
    """Status of a pipeline stage."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class PipelineStageEnum(str, Enum):
    """Pipeline stage identifiers."""

    EXTRACT = "extract"
    FILTER = "filter"
    VALIDATE = "validate"
    EMBED = "embed"
    TRANSLATE = "translate"
    STORE = "store"

    @classmethod
    def all(cls) -> list:
        return [cls.EXTRACT, cls.FILTER, cls.VALIDATE, cls.EMBED, cls.TRANSLATE, cls.STORE]


class BuildPipelineStatus(Enum):
    """Overall pipeline status."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"  # Some stages completed, others failed


@dataclass(frozen=True, slots=True)
class StageExecution:
    """
    Single stage execution in the glossary build pipeline.

    Each stage is independently testable and can be run as an HTTP endpoint.

    Stages (Unix Philosophy - one thing well):
    1. EXTRACT - NLTK NER + pattern extraction from raw text
    2. FILTER - Deduplication against existing glossary
    3. VALIDATE - LLM validation & classification
    4. EMBED - Generate vector embeddings
    5. TRANSLATE - LLM translation suggestions
    6. STORE - Persist to database
    """

    name: str
    status: PipelineStageStatus = PipelineStageStatus.PENDING
    input_data: Dict[str, Any] = field(default_factory=dict)
    output_data: Dict[str, Any] = field(default_factory=dict)
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    retry_count: int = 0

    @property
    def duration_seconds(self) -> Optional[float]:
        """Duration in seconds if completed."""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None

    def running(self) -> "StageExecution":
        """Mark stage as running."""
        return StageExecution(
            name=self.name,
            status=PipelineStageStatus.RUNNING,
            input_data=self.input_data,
            output_data=self.output_data,
            error_message=self.error_message,
            started_at=datetime.utcnow(),
            completed_at=self.completed_at,
            retry_count=self.retry_count,
        )

    def completed(self, output: Dict[str, Any]) -> "StageExecution":
        """Mark stage as completed with output."""
        return StageExecution(
            name=self.name,
            status=PipelineStageStatus.COMPLETED,
            input_data=self.input_data,
            output_data=output,
            error_message=None,
            started_at=self.started_at,
            completed_at=datetime.utcnow(),
            retry_count=self.retry_count,
        )

    def failed(self, error: str) -> "StageExecution":
        """Mark stage as failed."""
        return StageExecution(
            name=self.name,
            status=PipelineStageStatus.FAILED,
            input_data=self.input_data,
            output_data=self.output_data,
            error_message=error,
            started_at=self.started_at,
            completed_at=datetime.utcnow(),
            retry_count=self.retry_count,
        )

    def retry(self) -> "StageExecution":
        """Increment retry count and reset to pending."""
        return StageExecution(
            name=self.name,
            status=PipelineStageStatus.PENDING,
            input_data=self.input_data,
            output_data={},
            error_message=None,
            started_at=None,
            completed_at=None,
            retry_count=self.retry_count + 1,
        )


@dataclass(frozen=True, slots=True)
class BuildPipeline:
    """
    Glossary build pipeline aggregate.

    Orchestrates stages in sequence, managing state transitions.
    Each stage can be invoked independently via HTTP.
    """

    id: uuid.UUID = field(default_factory=uuid.uuid4)
    work_id: int = 0
    volume_id: int = 0
    source_text: str = ""
    source_lang: str = "en"
    target_lang: str = "es"
    min_frequency: int = 2
    dry_run: bool = False
    status: BuildPipelineStatus = BuildPipelineStatus.PENDING
    stages: List[StageExecution] = field(default_factory=list)
    current_stage_index: int = 0
    filtered_count: int = 0
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def __post_init__(self):
        if self.work_id <= 0:
            raise ValueError("work_id must be > 0")
        if self.volume_id <= 0:
            raise ValueError("volume_id must be > 0")
        if not self.source_text.strip():
            raise ValueError("source_text cannot be empty")
        if self.source_lang == self.target_lang:
            raise ValueError("Source and target languages must differ")
        if self.min_frequency < 1:
            raise ValueError("min_frequency must be >= 1")

        # Initialize stages if empty
        if not self.stages:
            object.__setattr__(self, "stages", [
                StageExecution(name=name) for name in PipelineStageEnum.all()
            ])

    def get_stage(self, name: str) -> Optional[StageExecution]:
        """Get stage by name."""
        for stage in self.stages:
            if stage.name == name:
                return stage
        return None

    def get_current_stage(self) -> Optional[StageExecution]:
        """Get the currently running/pending stage."""
        if 0 <= self.current_stage_index < len(self.stages):
            return self.stages[self.current_stage_index]
        return None

    def start_stage(self, name: str, input_data: Dict[str, Any]) -> "BuildPipeline":
        """Start a stage with input data."""
        stage = self.get_stage(name)
        if not stage:
            raise ValueError(f"Unknown stage: {name}")

        if stage.status != PipelineStageStatus.PENDING:
            raise ValueError(f"Stage {name} is not pending (current: {stage.status.value})")

        updated_stages = [
            s.running() if s.name == name else s
            for s in self.stages
        ]
        return self._replace(
            stages=updated_stages,
            status=BuildPipelineStatus.RUNNING,
            current_stage_index=PipelineStageEnum.all().index(name),
            updated_at=datetime.utcnow(),
        )

    def complete_stage(self, name: str, output_data: Dict[str, Any]) -> "BuildPipeline":
        """Complete a stage with output data."""
        stage = self.get_stage(name)
        if not stage:
            raise ValueError(f"Unknown stage: {name}")

        updated_stages = [
            s.completed(output_data) if s.name == name else s
            for s in self.stages
        ]

        # Check if all stages done
        next_idx = self.current_stage_index + 1
        if next_idx < len(PipelineStageEnum.all()):
            next_status = BuildPipelineStatus.RUNNING
        else:
            all_completed = all(s.status == PipelineStageStatus.COMPLETED for s in updated_stages)
            any_failed = any(s.status == PipelineStageStatus.FAILED for s in updated_stages)
            if any_failed:
                next_status = BuildPipelineStatus.FAILED
            elif all_completed:
                next_status = BuildPipelineStatus.COMPLETED
            else:
                next_status = BuildPipelineStatus.PARTIAL

        return self._replace(
            stages=updated_stages,
            status=next_status,
            current_stage_index=next_idx if next_idx < len(PipelineStageEnum.all()) else self.current_stage_index,
            updated_at=datetime.utcnow(),
        )

    def fail_stage(self, name: str, error: str) -> "BuildPipeline":
        """Mark a stage as failed."""
        stage = self.get_stage(name)
        if not stage:
            raise ValueError(f"Unknown stage: {name}")

        updated_stages = [
            s.failed(error) if s.name == name else s
            for s in self.stages
        ]
        return self._replace(
            stages=updated_stages,
            status=BuildPipelineStatus.FAILED,
            updated_at=datetime.utcnow(),
        )

    def record_filtered(self, count: int) -> "BuildPipeline":
        """Record number of filtered entities."""
        return self._replace(filtered_count=self.filtered_count + count)

    def _replace(self, **changes) -> "BuildPipeline":
        """Create new pipeline with updated fields."""
        return BuildPipeline(
            id=self.id,
            work_id=self.work_id,
            volume_id=self.volume_id,
            source_text=self.source_text,
            source_lang=self.source_lang,
            target_lang=self.target_lang,
            min_frequency=self.min_frequency,
            dry_run=self.dry_run,
            status=self.status,
            stages=self.stages,
            current_stage_index=self.current_stage_index,
            filtered_count=self.filtered_count,
            created_at=self.created_at,
            updated_at=self.updated_at,
            **changes,
        )

    @property
    def progress_percent(self) -> float:
        """Pipeline progress as percentage."""
        completed = sum(1 for s in self.stages if s.status == PipelineStageStatus.COMPLETED)
        return (completed / len(self.stages)) * 100

    @property
    def is_complete(self) -> bool:
        """Check if pipeline fully completed."""
        return self.status == BuildPipelineStatus.COMPLETED

    @property
    def has_failures(self) -> bool:
        """Check if any stage failed."""
        return any(s.status == PipelineStageStatus.FAILED for s in self.stages)

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "id": str(self.id),
            "work_id": self.work_id,
            "volume_id": self.volume_id,
            "source_lang": self.source_lang,
            "target_lang": self.target_lang,
            "min_frequency": self.min_frequency,
            "dry_run": self.dry_run,
            "status": self.status.value,
            "progress_percent": self.progress_percent,
            "stages": [
                {
                    "name": s.name,
                    "status": s.status.value,
                    "duration_seconds": s.duration_seconds,
                    "error": s.error_message,
                    "retry_count": s.retry_count,
                }
                for s in self.stages
            ],
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


# Backward compatibility aliases
PipelineStage = PipelineStageEnum
PipelineStages = PipelineStageEnum