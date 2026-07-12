"""
CloudEvents 1.0 Implementation for PDFTranslator.

Provides CloudEvent creation, serialization, and parsing utilities.
Compatible with Python cloudevents-sdk and manual HTTP/Kafka headers.
"""

from __future__ import annotations
import json
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Union, List, TypeVar, Generic

try:
    from cloudevents.http import CloudEvent as SDKCloudEvent
    from cloudevents.conversion import to_json, to_structured
    CE_SDK_AVAILABLE = True
except ImportError:
    CE_SDK_AVAILABLE = False

# Type variable for payload
T = TypeVar('T')


@dataclass
class CloudEvent(Generic[T]):
    """
    CloudEvents 1.0 event representation.

    Attributes:
        specversion: CloudEvents spec version (always "1.0")
        id: Unique event identifier (UUID v4)
        type: Event type URI (e.g., "com.pdftranslator.catalog.work.created")
        source: Source service URI (e.g., "/pdftranslator/catalog-service")
        data: Event payload (Any JSON-serializable or CloudEvents SDK compatible)
        datacontenttype: MIME type of data (default: "application/json" or "application/avro")
        subject: Resource identifier (e.g., "work/uuid", "job/uuid")
        time: Event timestamp (RFC 3339)
        data_base64: Base64-encoded binary data (for Avro payloads)
        extensions: Custom extension attributes
    """

    # Required attributes (CloudEvents spec)
    specversion: str = "1.0"
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    type: str = ""
    source: str = ""
    data: Optional[T] = None
    datacontenttype: str = "application/json"

    # Optional spec attributes
    subject: Optional[str] = None
    time: Optional[str] = None

    # Custom extensions
    data_base64: Optional[str] = None
    extensions: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Set defaults after initialization."""
        if self.time is None:
            self.time = datetime.now(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00', 'Z')

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        result = {
            "specversion": self.specversion,
            "id": self.id,
            "type": self.type,
            "source": self.source,
            "datacontenttype": self.datacontenttype,
        }

        if self.subject is not None:
            result["subject"] = self.subject
        if self.time is not None:
            result["time"] = self.time

        # Handle data vs data_base64
        if self.data_base64 is not None:
            result["data_base64"] = self.data_base64
        elif self.data is not None:
            result["data"] = self.data

        # Add extensions
        result.update(self.extensions)

        return result

    def to_json(self) -> str:
        """Serialize to JSON string."""
        return json.dumps(self.to_dict())

    def to_http_headers(self) -> Dict[str, str]:
        """Convert to CloudEvents HTTP binary mode headers."""
        headers = {
            "Ce-Specversion": self.specversion,
            "Ce-Id": self.id,
            "Ce-Type": self.type,
            "Ce-Source": self.source,
            "Ce-Datacontenttype": self.datacontenttype,
        }

        if self.subject:
            headers["Ce-Subject"] = self.subject
        if self.time:
            headers["Ce-Time"] = self.time

        # Extensions become Ce-* headers
        for key, value in self.extensions.items():
            header_key = f"Ce-{key.replace('_', '-')}"
            headers[header_key] = str(value)

        return headers

    def to_structured_json(self) -> str:
        """Serialize as CloudEvents structured mode (single JSON object)."""
        if CE_SDK_AVAILABLE:
            sdk_event = self._to_sdk_event()
            return to_json(sdk_event)
        return self.to_json()

    def _to_sdk_event(self) -> "SDKCloudEvent":
        """Convert to cloudevents-sdk CloudEvent."""
        if not CE_SDK_AVAILABLE:
            raise RuntimeError("cloudevents-sdk not installed")

        attributes = {
            "specversion": self.specversion,
            "id": self.id,
            "type": self.type,
            "source": self.source,
            "datacontenttype": self.datacontenttype,
        }

        if self.subject:
            attributes["subject"] = self.subject
        if self.time:
            attributes["time"] = self.time

        attributes.update(self.extensions)

        if self.data_base64:
            data = self.data_base64
        else:
            data = self.data

        return SDKCloudEvent(attributes, data)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CloudEvent":
        """Create CloudEvent from dictionary."""
        # Extract known attributes
        known_attrs = {
            'specversion', 'id', 'type', 'source', 'datacontenttype',
            'subject', 'time', 'data', 'data_base64'
        }

        init_args = {}
        extensions = {}

        for key, value in data.items():
            if key in known_attrs:
                init_args[key] = value
            else:
                extensions[key] = value

        init_args['extensions'] = extensions
        return cls(**init_args)

    @classmethod
    def from_json(cls, json_str: str) -> "CloudEvent":
        """Create CloudEvent from JSON string."""
        return cls.from_dict(json.loads(json_str))

    @classmethod
    def from_http_headers(
        cls,
        headers: Dict[str, str],
        body: Optional[Union[bytes, str]] = None,
    ) -> "CloudEvent":
        """
        Parse CloudEvent from HTTP headers (binary mode) + body.

        Args:
            headers: HTTP headers dict (case-insensitive)
            body: Request body (bytes or string)

        Returns:
            CloudEvent instance
        """
        # Normalize headers to lowercase
        norm_headers = {k.lower(): v for k, v in headers.items()}

        # Extract required attributes
        init_args = {
            "specversion": norm_headers.get("ce-specversion", "1.0"),
            "id": norm_headers.get("ce-id", ""),
            "type": norm_headers.get("ce-type", ""),
            "source": norm_headers.get("ce-source", ""),
            "datacontenttype": norm_headers.get("ce-datacontenttype", "application/json"),
        }

        # Optional attributes
        if "ce-subject" in norm_headers:
            init_args["subject"] = norm_headers["ce-subject"]
        if "ce-time" in norm_headers:
            init_args["time"] = norm_headers["ce-time"]

        # Extract extensions (ce-* headers not in known list)
        known_headers = {
            'ce-specversion', 'ce-id', 'ce-type', 'ce-source',
            'ce-datacontenttype', 'ce-subject', 'ce-time'
        }
        extensions = {}
        for key, value in norm_headers.items():
            if key.startswith("ce-") and key not in known_headers:
                ext_key = key[3:].replace('-', '_')  # Remove 'ce-' prefix
                extensions[ext_key] = value

        init_args["extensions"] = extensions

        # Handle body
        if body is not None:
            content_type = init_args["datacontenttype"]
            if content_type == "application/avro" or content_type == "application/octet-stream":
                init_args["data_base64"] = body.decode('ascii') if isinstance(body, bytes) else body
            else:
                try:
                    init_args["data"] = json.loads(body) if isinstance(body, (bytes, str)) else body
                except json.JSONDecodeError:
                    init_args["data"] = body

        return cls(**init_args)

    @classmethod
    def from_kafka_record(
        cls,
        headers: List[tuple],
        value: bytes,
    ) -> "CloudEvent":
        """
        Parse CloudEvent from Kafka record headers + value.

        Args:
            headers: List of (key, value) tuples from Kafka record
            value: Kafka record value (bytes)

        Returns:
            CloudEvent instance
        """
        # Convert Kafka headers to dict
        header_dict = {k: v.decode('utf-8') if isinstance(v, bytes) else v for k, v in headers}
        return cls.from_http_headers(header_dict, value)


def create_event(
    event_type: str,
    source: str,
    payload: Dict[str, Any],
    subject: Optional[str] = None,
    trace_id: Optional[str] = None,
    span_id: Optional[str] = None,
    trace_flags: Optional[str] = None,
    event_version: int = 1,
    correlation_id: Optional[str] = None,
    causation_id: Optional[str] = None,
    partition_key: Optional[str] = None,
    datacontenttype: str = "application/json",
) -> CloudEvent:
    """
    Factory function to create a CloudEvent with PDFTranslator conventions.

    Args:
        event_type: Event type URI (e.g., "com.pdftranslator.catalog.work.created")
        source: Source service URI (e.g., "/pdftranslator/catalog-service")
        payload: Event payload dict
        subject: Resource identifier (auto-generated from type if not provided)
        trace_id: W3C traceparent trace-id
        span_id: W3C traceparent span-id
        trace_flags: W3C trace-flags (e.g., "01" for sampled)
        event_version: Schema version number
        correlation_id: Business correlation ID
        causation_id: ID of event that caused this event
        partition_key: Kafka partition key
        datacontenttype: Payload MIME type

    Returns:
        CloudEvent instance
    """
    # Auto-generate subject from event type if not provided
    if subject is None:
        # e.g., "com.pdftranslator.catalog.work.created" -> "work"
        parts = event_type.split('.')
        if len(parts) >= 4:
            subject = parts[3]  # work, job, glossary, etc.

    extensions = {
        "eventversion": event_version,
    }

    if trace_id:
        extensions["traceid"] = trace_id
    if span_id:
        extensions["spanid"] = span_id
    if trace_flags:
        extensions["traceflags"] = trace_flags
    if correlation_id:
        extensions["correlationid"] = correlation_id
    if causation_id:
        extensions["causationid"] = causation_id
    if partition_key:
        extensions["partitionkey"] = partition_key

    return CloudEvent(
        type=event_type,
        source=source,
        data=payload,
        subject=subject,
        datacontenttype=datacontenttype,
        extensions=extensions,
    )


# Event Type Constants
class EventTypes:
    """Centralized event type constants."""

    # Catalog Service
    WORK_CREATED = "com.pdftranslator.catalog.work.created"
    WORK_UPDATED = "com.pdftranslator.catalog.work.updated"
    WORK_DELETED = "com.pdftranslator.catalog.work.deleted"
    VOLUME_CREATED = "com.pdftranslator.catalog.volume.created"
    VOLUME_UPDATED = "com.pdftranslator.catalog.volume.updated"
    VOLUME_DELETED = "com.pdftranslator.catalog.volume.deleted"
    CHAPTER_CREATED = "com.pdftranslator.catalog.chapter.created"
    CHAPTER_UPDATED = "com.pdftranslator.catalog.chapter.updated"
    CHAPTER_DELETED = "com.pdftranslator.catalog.chapter.deleted"

    # Document Service
    DOCUMENT_EXTRACTED = "com.pdftranslator.document.extracted"
    DOCUMENT_FAILED = "com.pdftranslator.document.failed"

    # Glossary Service
    GLOSSARY_BUILT = "com.pdftranslator.glossary.built"
    GLOSSARY_UPDATED = "com.pdftranslator.glossary.updated"
    GLOSSARY_DELETED = "com.pdftranslator.glossary.deleted"

    # Translation Service
    JOB_QUEUED = "com.pdftranslator.translation.job.queued"
    JOB_STARTED = "com.pdftranslator.translation.job.started"
    JOB_COMPLETED = "com.pdftranslator.translation.job.completed"
    JOB_FAILED = "com.pdftranslator.translation.job.failed"
    JOB_PAUSED = "com.pdftranslator.translation.job.paused"
    JOB_RESUMED = "com.pdftranslator.translation.job.resumed"
    JOB_CANCELLED = "com.pdftranslator.translation.job.cancelled"
    SEGMENT_TRANSLATED = "com.pdftranslator.translation.segment.translated"

    # Job Orchestrator
    WORKFLOW_STARTED = "com.pdftranslator.job.workflow.started"
    WORKFLOW_COMPLETED = "com.pdftranslator.job.workflow.completed"
    WORKFLOW_FAILED = "com.pdftranslator.job.workflow.failed"
    WORKFLOW_STEP_COMPLETED = "com.pdftranslator.job.workflow.step.completed"

    # Audio Service
    AUDIOBOOK_GENERATED = "com.pdftranslator.audio.audiobook.generated"
    AUDIOBOOK_FAILED = "com.pdftranslator.audio.audiobook.failed"

    # Error
    ERROR = "com.pdftranslator.error"


class EventSources:
    """Centralized event source constants."""

    CATALOG_SERVICE = "/pdftranslator/catalog-service"
    DOCUMENT_SERVICE = "/pdftranslator/document-service"
    GLOSSARY_SERVICE = "/pdftranslator/glossary-service"
    TRANSLATION_SERVICE = "/pdftranslator/translation-service"
    JOB_ORCHESTRATOR = "/pdftranslator/job-orchestrator"
    AUDIO_SERVICE = "/pdftranslator/audio-service"