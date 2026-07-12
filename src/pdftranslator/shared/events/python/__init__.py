"""
Shared Event Models for PDFTranslator (Generated from Avro schemas).

This package provides:
1. Python dataclasses for all event payloads (generated from Avro)
2. CloudEvents 1.0 envelope handling
3. Avro serialization with Schema Registry support
4. Kafka producer/consumer helpers
"""

from .cloudevents import (
    CloudEvent,
    EventMetadata,
    EventTypes,
    EventSources,
    create_event,
)
from .serialization import (
    AvroSerializer,
    SchemaRegistryClient,
    serialize_event,
    deserialize_event,
)

__all__ = [
    # CloudEvents
    "CloudEvent",
    "EventMetadata",
    "EventTypes",
    "EventSources",
    "create_event",
    # Serialization
    "AvroSerializer",
    "SchemaRegistryClient",
    "serialize_event",
    "deserialize_event",
]

__version__ = "0.4.0"