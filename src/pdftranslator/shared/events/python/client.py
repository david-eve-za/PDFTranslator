"""
Kafka Event Publisher Client for PDFTranslator.

Provides high-level async interface for publishing CloudEvents to Kafka topics.
"""

from __future__ import annotations
import asyncio
import logging
import os
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from confluent_kafka import Producer, KafkaException

from .cloudevents import (
    CloudEvent,
    EventTypes,
    EventSources,
    create_event,
)

logger = logging.getLogger(__name__)


@dataclass
class KafkaConfig:
    """Configuration for Kafka producer."""
    bootstrap_servers: str = field(default_factory=lambda: os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092"))
    client_id: str = "pdftranslator"
    acks: str = "all"
    retries: int = 3
    retry_backoff_ms: int = 1000
    linger_ms: int = 5
    batch_size: int = 16384
    compression_type: str = "snappy"
    security_protocol: str = "PLAINTEXT"
    sasl_mechanism: Optional[str] = None
    sasl_username: Optional[str] = None
    sasl_password: Optional[str] = None


@dataclass
class TopicConfig:
    """Configuration for topic creation."""
    name: str
    partitions: int = 3
    replication_factor: int = 1
    config: Dict[str, str] = field(default_factory=dict)


class EventPublisher:
    """
    Async Kafka producer for CloudEvents.

    Usage:
        publisher = EventPublisher(KafkaConfig())
        await publisher.publish(event)
        await publisher.flush()
    """

    def __init__(
        self,
        config: Optional[KafkaConfig] = None,
        loop: Optional[asyncio.AbstractEventLoop] = None,
    ):
        self.config = config or KafkaConfig()
        self._loop = loop or asyncio.get_event_loop()
        self._producer: Optional[Producer] = None
        self._running = False
        self._poll_task: Optional[asyncio.Task] = None

    def _create_producer(self) -> Producer:
        """Create Kafka producer with configuration."""
        producer_config = {
            "bootstrap.servers": self.config.bootstrap_servers,
            "client.id": self.config.client_id,
            "acks": self.config.acks,
            "retries": self.config.retries,
            "retry.backoff.ms": self.config.retry_backoff_ms,
            "linger.ms": self.config.linger_ms,
            "batch.size": self.config.batch_size,
            "compression.type": self.config.compression_type,
            "security.protocol": self.config.security_protocol,
        }

        # Add SASL config if provided
        if self.config.sasl_mechanism:
            producer_config.update({
                "sasl.mechanism": self.config.sasl_mechanism,
                "sasl.username": self.config.sasl_username,
                "sasl.password": self.config.sasl_password,
            })

        return Producer(producer_config)

    async def start(self) -> None:
        """Initialize the producer and start background poll loop."""
        if self._running:
            return

        self._producer = self._create_producer()
        self._running = True
        self._poll_task = self._loop.create_task(self._poll_loop())
        logger.info(f"EventPublisher started: {self.config.bootstrap_servers}")

    async def stop(self) -> None:
        """Stop producer and flush pending messages."""
        if not self._running:
            return

        self._running = False

        if self._poll_task:
            self._poll_task.cancel()
            try:
                await self._poll_task
            except asyncio.CancelledError:
                pass

        await self.flush()

        if self._producer:
            self._producer = None

        logger.info("EventPublisher stopped")

    async def _poll_loop(self) -> None:
        """Background poll loop for delivery callbacks."""
        while self._running:
            try:
                self._producer.poll(0.1)
                await asyncio.sleep(0.1)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Poll loop error: {e}")
                await asyncio.sleep(1)

    def _delivery_callback(self, err, msg):
        """Callback for message delivery reports."""
        if err:
            logger.error(f"Message delivery failed: {err} - Topic: {msg.topic()}, Partition: {msg.partition()}")
        else:
            logger.debug(f"Message delivered: Topic: {msg.topic()}, Partition: {msg.partition()}, Offset: {msg.offset()}")

    async def publish(
        self,
        event: CloudEvent,
        topic: Optional[str] = None,
        key: Optional[bytes] = None,
        partition: Optional[int] = None,
    ) -> bool:
        """
        Publish a CloudEvent to Kafka.

        Args:
            event: CloudEvent to publish
            topic: Override topic (default: derived from event type)
            key: Partition key (default: event subject or trace ID)
            partition: Specific partition (optional)

        Returns:
            True if message was queued for delivery
        """
        if not self._running or not self._producer:
            raise RuntimeError("EventPublisher not started. Call start() first.")

        # Derive topic from event type if not provided
        if topic is None:
            topic = event.type.replace("com.pdftranslator.", "pdftranslator.")

        # Use subject or trace ID as key for partitioning
        if key is None:
            key_value = event.subject or event.extensions.get("traceid", event.id)
            key = key_value.encode() if key_value else None

        # Serialize event to JSON (could be Avro with schema registry)
        value = event.to_json().encode()

        # Prepare headers for CloudEvents binary mode
        headers = [(k, v.encode() if isinstance(v, str) else v) for k, v in event.to_http_headers().items()]

        try:
            self._producer.produce(
                topic=topic,
                value=value,
                key=key,
                partition=partition,
                headers=headers,
                callback=self._delivery_callback,
            )
            # Trigger poll to process delivery callbacks
            self._producer.poll(0)
            return True
        except BufferError:
            logger.warning("Producer buffer full, waiting...")
            self._producer.poll(1000)
            return False
        except Exception as e:
            logger.error(f"Failed to publish event: {e}")
            raise

    async def publish_batch(
        self,
        events: list[CloudEvent],
        topic: Optional[str] = None,
    ) -> int:
        """Publish multiple events efficiently."""
        count = 0
        for event in events:
            if await self.publish(event, topic):
                count += 1
        return count

    async def flush(self, timeout: float = 10.0) -> int:
        """
        Flush pending messages.

        Returns:
            Number of messages still pending
        """
        if self._producer:
            return self._producer.flush(timeout)
        return 0

    def __enter__(self):
        raise TypeError("Use async with or call start()/stop() explicitly")

    def __exit__(self, *args):
        pass

    async def __aenter__(self) -> "EventPublisher":
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.stop()


class EventPublisherFactory:
    """Factory for creating and caching EventPublisher instances."""

    _instances: Dict[str, EventPublisher] = {}

    @classmethod
    def get_publisher(cls, config: Optional[KafkaConfig] = None, name: str = "default") -> EventPublisher:
        """Get or create a publisher instance."""
        if name not in cls._instances:
            cls._instances[name] = EventPublisher(config)
        return cls._instances[name]

    @classmethod
    async def close_all(cls) -> None:
        """Close all publisher instances."""
        for publisher in cls._instances.values():
            await publisher.stop()
        cls._instances.clear()


# Convenience functions for common workflow events

async def publish_workflow_started(
    publisher: EventPublisher,
    pipeline_id: str,
    job_id: int,
    work_id: int,
    source_lang: str,
    target_lang: str,
    trace_id: Optional[str] = None,
) -> None:
    """Publish JOB_STARTED event."""
    event = create_event(
        event_type=EventTypes.JOB_STARTED,
        source=EventSources.TRANSLATION_SERVICE,
        payload={
            "pipeline_id": pipeline_id,
            "job_id": job_id,
            "work_id": work_id,
            "source_lang": source_lang,
            "target_lang": target_lang,
        },
        subject=f"job/{job_id}",
        trace_id=trace_id,
        correlation_id=str(job_id),
    )
    await publisher.publish(event)


async def publish_workflow_completed(
    publisher: EventPublisher,
    pipeline_id: str,
    job_id: int,
    work_id: int,
    stages_completed: list[str],
    duration_ms: int,
    trace_id: Optional[str] = None,
) -> None:
    """Publish JOB_COMPLETED event."""
    event = create_event(
        event_type=EventTypes.JOB_COMPLETED,
        source=EventSources.TRANSLATION_SERVICE,
        payload={
            "pipeline_id": pipeline_id,
            "job_id": job_id,
            "work_id": work_id,
            "stages_completed": stages_completed,
            "duration_ms": duration_ms,
        },
        subject=f"job/{job_id}",
        trace_id=trace_id,
        correlation_id=str(job_id),
    )
    await publisher.publish(event)


async def publish_workflow_failed(
    publisher: EventPublisher,
    pipeline_id: str,
    job_id: int,
    work_id: int,
    error: str,
    failed_stage: Optional[str] = None,
    trace_id: Optional[str] = None,
) -> None:
    """Publish JOB_FAILED event."""
    event = create_event(
        event_type=EventTypes.JOB_FAILED,
        source=EventSources.TRANSLATION_SERVICE,
        payload={
            "pipeline_id": pipeline_id,
            "job_id": job_id,
            "work_id": work_id,
            "error": error,
            "failed_stage": failed_stage,
        },
        subject=f"job/{job_id}",
        trace_id=trace_id,
        correlation_id=str(job_id),
    )
    await publisher.publish(event)


async def publish_step_completed(
    publisher: EventPublisher,
    pipeline_id: str,
    job_id: int,
    work_id: int,
    stage: str,
    output: Dict[str, Any],
    duration_ms: int,
    trace_id: Optional[str] = None,
) -> None:
    """Publish WORKFLOW_STEP_COMPLETED event."""
    event = create_event(
        event_type=EventTypes.WORKFLOW_STEP_COMPLETED,
        source=EventSources.JOB_ORCHESTRATOR,
        payload={
            "pipeline_id": pipeline_id,
            "job_id": job_id,
            "work_id": work_id,
            "stage": stage,
            "output": output,
            "duration_ms": duration_ms,
        },
        subject=f"job/{job_id}",
        trace_id=trace_id,
        correlation_id=str(job_id),
    )
    await publisher.publish(event)


async def publish_audiobook_generated(
    publisher: EventPublisher,
    pipeline_id: str,
    job_id: int,
    audio_file_path: str,
    duration_ms: int,
    format: str,
    trace_id: Optional[str] = None,
) -> None:
    """Publish AUDIOBOOK_GENERATED event."""
    event = create_event(
        event_type=EventTypes.AUDIOBOOK_GENERATED,
        source=EventSources.AUDIO_SERVICE,
        payload={
            "pipeline_id": pipeline_id,
            "job_id": job_id,
            "audio_file_path": audio_file_path,
            "duration_ms": duration_ms,
            "format": format,
        },
        subject=f"job/{job_id}",
        trace_id=trace_id,
        correlation_id=str(job_id),
    )
    await publisher.publish(event)