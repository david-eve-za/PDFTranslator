"""
Event Publishing Activities for Translation Workflow.

Publishes CloudEvents to Kafka at workflow milestones.
"""
from __future__ import annotations
import os
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from temporalio import activity

from pdftranslator.shared.events import (
    EventPublisher,
    EventPublisherFactory,
    KafkaConfig,
    EventTypes,
    EventSources,
    create_event,
)


# Global publisher instance (singleton per worker)
_publisher_instance: Optional[EventPublisher] = None


@dataclass
class PublishEventInput:
    """Input for event publishing activities."""
    pipeline_id: str
    job_id: int
    work_id: Optional[int] = None
    event_type: Optional[str] = None
    source: Optional[str] = None
    trace_id: Optional[str] = None
    payload: Optional[Dict[str, Any]] = None

    # Stage-specific fields
    source_lang: Optional[str] = None
    target_lang: Optional[str] = None
    stages_completed: list[str] = field(default_factory=list)
    duration_ms: int = 0
    stage: Optional[str] = None
    output: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    failed_stage: Optional[str] = None
    audio_file_path: Optional[str] = None
    format: Optional[str] = None

    def get(self, key: str, default=None):
        """Allow dict-like access for backward compatibility."""
        return getattr(self, key, default)


@dataclass
class PublishEventOutput:
    """Output for event publishing activities."""
    success: bool
    event_id: Optional[str] = None
    topic: Optional[str] = None
    error: Optional[str] = None


@activity.defn
async def publish_job_started_activity(input_data: PublishEventInput) -> PublishEventOutput:
    """Publish JOB_STARTED event."""
    return await _publish_workflow_event(
        event_type=EventTypes.JOB_STARTED,
        source=EventSources.TRANSLATION_SERVICE,
        pipeline_id=input_data.pipeline_id,
        job_id=input_data.job_id,
        work_id=input_data.get("work_id"),
        trace_id=input_data.get("trace_id"),
        payload={
            "pipeline_id": input_data.pipeline_id,
            "job_id": input_data.job_id,
            "work_id": input_data.get("work_id"),
            "source_lang": input_data.get("source_lang"),
            "target_lang": input_data.get("target_lang"),
        },
    )


@activity.defn
async def publish_job_completed_activity(input_data: PublishEventInput) -> PublishEventOutput:
    """Publish JOB_COMPLETED event."""
    return await _publish_workflow_event(
        event_type=EventTypes.JOB_COMPLETED,
        source=EventSources.TRANSLATION_SERVICE,
        pipeline_id=input_data.pipeline_id,
        job_id=input_data.job_id,
        work_id=input_data.get("work_id"),
        trace_id=input_data.get("trace_id"),
        payload={
            "pipeline_id": input_data.pipeline_id,
            "job_id": input_data.job_id,
            "work_id": input_data.get("work_id"),
            "stages_completed": input_data.get("stages_completed", []),
            "duration_ms": input_data.get("duration_ms", 0),
        },
    )


@activity.defn
async def publish_job_failed_activity(input_data: PublishEventInput) -> PublishEventOutput:
    """Publish JOB_FAILED event."""
    return await _publish_workflow_event(
        event_type=EventTypes.JOB_FAILED,
        source=EventSources.TRANSLATION_SERVICE,
        pipeline_id=input_data.pipeline_id,
        job_id=input_data.job_id,
        work_id=input_data.get("work_id"),
        trace_id=input_data.get("trace_id"),
        payload={
            "pipeline_id": input_data.pipeline_id,
            "job_id": input_data.job_id,
            "work_id": input_data.get("work_id"),
            "error": input_data.get("error", "Unknown error"),
            "failed_stage": input_data.get("failed_stage"),
        },
    )


@activity.defn
async def publish_step_completed_activity(input_data: PublishEventInput) -> PublishEventOutput:
    """Publish WORKFLOW_STEP_COMPLETED event."""
    return await _publish_workflow_event(
        event_type=EventTypes.WORKFLOW_STEP_COMPLETED,
        source=EventSources.JOB_ORCHESTRATOR,
        pipeline_id=input_data.pipeline_id,
        job_id=input_data.job_id,
        work_id=input_data.get("work_id"),
        trace_id=input_data.get("trace_id"),
        payload={
            "pipeline_id": input_data.pipeline_id,
            "job_id": input_data.job_id,
            "work_id": input_data.get("work_id"),
            "stage": input_data.get("stage"),
            "output": input_data.get("output", {}),
            "duration_ms": input_data.get("duration_ms", 0),
        },
    )


@activity.defn
async def publish_audiobook_generated_activity(input_data: PublishEventInput) -> PublishEventOutput:
    """Publish AUDIOBOOK_GENERATED event."""
    return await _publish_workflow_event(
        event_type=EventTypes.AUDIOBOOK_GENERATED,
        source=EventSources.AUDIO_SERVICE,
        pipeline_id=input_data.pipeline_id,
        job_id=input_data.job_id,
        work_id=input_data.get("work_id"),
        trace_id=input_data.get("trace_id"),
        payload={
            "pipeline_id": input_data.pipeline_id,
            "job_id": input_data.job_id,
            "work_id": input_data.get("work_id"),
            "audio_file_path": input_data.get("audio_file_path"),
            "duration_ms": input_data.get("duration_ms", 0),
            "format": input_data.get("format", "m4a"),
        },
    )


@activity.defn
async def publish_event_activity(input_data: PublishEventInput) -> PublishEventOutput:
    """Generic event publisher for custom events."""
    return await _publish_workflow_event(
        event_type=input_data.event_type,
        source=input_data.source,
        pipeline_id=input_data.pipeline_id,
        job_id=input_data.job_id,
        work_id=input_data.get("work_id"),
        trace_id=input_data.get("trace_id"),
        payload=input_data.payload or {},
    )


async def _publish_workflow_event(
    event_type: str,
    source: str,
    pipeline_id: str,
    job_id: int,
    work_id: Optional[int] = None,
    trace_id: Optional[str] = None,
    payload: Optional[Dict[str, Any]] = None,
) -> PublishEventOutput:
    """Internal helper to publish a workflow event."""
    global _publisher_instance

    try:
        # Get or create publisher
        if _publisher_instance is None:
            config = KafkaConfig(
                bootstrap_servers=os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092"),
                client_id=f"pdftranslator-translation-worker-{os.getpid()}",
            )
            _publisher_instance = EventPublisherFactory.get_publisher("translation-workflow", config)
            await _publisher_instance.start()

        # Build subject and correlation ID
        subject_parts = [f"pipeline/{pipeline_id}", f"job/{job_id}"]
        if work_id:
            subject_parts.append(f"work/{work_id}")
        subject = "/".join(subject_parts)

        correlation_id = f"job-{job_id}"
        if work_id:
            correlation_id = f"job-{job_id}-work-{work_id}"

        # Create CloudEvent
        event = create_event(
            event_type=event_type,
            source=source,
            payload=payload or {},
            subject=subject,
            trace_id=trace_id,
            correlation_id=correlation_id,
        )

        # Publish
        await _publisher_instance.publish(event)

        return PublishEventOutput(
            success=True,
            event_id=event.id,
            topic=event.type.replace("com.pdftranslator.", "pdftranslator."),
        )

    except Exception as e:
        activity.logger.error(f"Failed to publish event {event_type}: {e}")
        return PublishEventOutput(
            success=False,
            error=str(e),
        )


async def shutdown_publisher():
    """Shutdown the publisher instance."""
    global _publisher_instance
    if _publisher_instance:
        await _publisher_instance.stop()
        _publisher_instance = None