"""
Avro Serialization with Schema Registry Support.

Provides high-level functions for serializing/deserializing CloudEvents
with Avro payloads using Confluent/Apicurio Schema Registry.
"""

from __future__ import annotations
import json
import struct
from dataclasses import dataclass
from typing import Any, Optional, Dict, Union, Tuple
from urllib.parse import urljoin

import httpx

try:
    import fastavro
    FASTAVRO_AVAILABLE = True
except ImportError:
    fastavro = None
    FASTAVRO_AVAILABLE = False


@dataclass
class SchemaRegistryConfig:
    """Configuration for Schema Registry client."""
    url: str = "http://localhost:8081"
    timeout: float = 10.0
    auth: Optional[Tuple[str, str]] = None  # (username, password)
    ssl_verify: bool = True


class SchemaRegistryClient:
    """
    Client for Confluent Schema Registry / Apicurio Registry.

    Handles schema registration, lookup, and caching.
    """

    def __init__(self, config: Optional[SchemaRegistryConfig] = None):
        self.config = config or SchemaRegistryConfig()
        self._id_cache: Dict[int, Dict] = {}  # schema_id -> parsed schema
        self._subject_cache: Dict[str, Dict] = {}  # subject -> latest schema

    def _client(self) -> httpx.Client:
        return httpx.Client(
            base_url=self.config.url,
            timeout=self.config.timeout,
            auth=self.config.auth,
            verify=self.config.ssl_verify,
        )

    def register(self, subject: str, schema: Dict, schema_type: str = "AVRO") -> int:
        """
        Register a new schema version.

        Args:
            subject: Subject name (e.g., "pdftranslator.work.created-value")
            schema: Parsed Avro schema dict
            schema_type: "AVRO", "JSON", "PROTOBUF"

        Returns:
            Global schema ID assigned by registry
        """
        with self._client() as client:
            response = client.post(
                f"/subjects/{subject}/versions",
                headers={
                    "Content-Type": "application/vnd.schemaregistry.v1+json",
                },
                json={"schema": json.dumps(schema), "schema_type": schema_type},
            )
            response.raise_for_status()
            result = response.json()
            schema_id = result["id"]

            # Update caches
            self._id_cache[schema_id] = schema
            self._subject_cache[subject] = schema
            return schema_id

    def get_by_id(self, schema_id: int) -> Dict:
        """Get schema by global ID."""
        if schema_id in self._id_cache:
            return self._id_cache[schema_id]

        with self._client() as client:
            response = client.get(f"/schemas/ids/{schema_id}")
            response.raise_for_status()
            data = response.json()
            schema = json.loads(data["schema"]) if isinstance(data["schema"], str) else data["schema"]
            self._id_cache[schema_id] = schema
            return schema

    def get_latest(self, subject: str) -> Dict:
        """Get latest schema for subject."""
        if subject in self._subject_cache:
            return self._subject_cache[subject]

        with self._client() as client:
            response = client.get(f"/subjects/{subject}/versions/latest")
            response.raise_for_status()
            data = response.json()
            schema = json.loads(data["schema"]) if isinstance(data["schema"], str) else data["schema"]
            self._subject_cache[subject] = schema
            return schema

    def check_compatibility(self, subject: str, schema: Dict) -> bool:
        """Check if schema is compatible with latest version."""
        with self._client() as client:
            response = client.post(
                f"/compatibility/subjects/{subject}/versions",
                headers={"Content-Type": "application/vnd.schemaregistry.v1+json"},
                json={"schema": json.dumps(schema)},
            )
            response.raise_for_status()
            return response.json().get("is_compatible", False)


class AvroSerializer:
    """
    Avro serializer with Schema Registry integration.

    Handles:
    - Binary encoding/decoding with schema ID prefix (Confluent wire format)
    - Schema registration on first use
    - Schema caching
    """

    # Confluent wire format: magic byte (0) + schema ID (4 bytes, big-endian)
    MAGIC_BYTE = b'\x00'

    def __init__(self, registry: SchemaRegistryClient):
        self.registry = registry
        self._parsed_schemas: Dict[int, Any] = {}  # schema_id -> parsed schema
        self._subject_schemas: Dict[str, Tuple[int, Any]] = {}  # subject -> (schema_id, parsed_schema)

    def _get_parsed_schema(self, schema_id: int) -> Any:
        """Get parsed fastavro schema from cache or registry."""
        if schema_id not in self._parsed_schemas:
            schema = self.registry.get_by_id(schema_id)
            self._parsed_schemas[schema_id] = fastavro.parse_schema(schema)
        return self._parsed_schemas[schema_id]

    def _get_or_register_schema(self, subject: str, schema: Dict) -> Tuple[int, Any]:
        """Get cached or register new schema for subject."""
        if subject in self._subject_schemas:
            schema_id, parsed = self._subject_schemas[subject]
            return schema_id, parsed

        # Try to get latest from registry first
        try:
            latest_schema = self.registry.get_latest(subject)
            schema_id = self._register_and_parse(subject, latest_schema)
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                # Register new schema
                schema_id = self.registry.register(subject, schema)
                schema_id, parsed = self._register_and_parse(subject, schema)
            else:
                raise

        return schema_id, parsed

    def _register_and_parse(self, subject: str, schema: Dict) -> Tuple[int, Any]:
        """Register schema and return parsed version."""
        schema_id = self.registry.register(subject, schema)
        parsed = fastavro.parse_schema(schema)
        self._subject_schemas[subject] = (schema_id, parsed)
        self._parsed_schemas[schema_id] = parsed
        return schema_id, parsed

    def serialize(self, subject: str, schema: Dict, data: Dict) -> bytes:
        """
        Serialize data to Avro binary with Confluent wire format.

        Args:
            subject: Schema Registry subject
            schema: Avro schema dict
            data: Data dict matching schema

        Returns:
            Binary payload: MAGIC_BYTE + schema_id (4 bytes, big-endian) + avro_data
        """
        if not FASTAVRO_AVAILABLE:
            raise RuntimeError("fastavro not installed. Install with: pip install fastavro")

        schema_id, parsed_schema = self._get_or_register_schema(subject, schema)

        # Encode to Avro binary
        import io
        buf = io.BytesIO()
        fastavro.schemaless_writer(buf, parsed_schema, data)
        avro_data = buf.getvalue()

        # Confluent wire format: magic byte + schema ID (big-endian) + avro data
        return self.MAGIC_BYTE + struct.pack('>I', schema_id) + avro_data

    def deserialize(self, payload: bytes) -> Tuple[int, Dict]:
        """
        Deserialize Avro binary with Confluent wire format.

        Args:
            payload: Binary payload (magic + schema_id + avro_data)

        Returns:
            Tuple of (schema_id, decoded_data)
        """
        if not FASTAVRO_AVAILABLE:
            raise RuntimeError("fastavro not installed. Install with: pip install fastavro")

        if len(payload) < 5:
            raise ValueError("Payload too short for Confluent wire format")

        # Verify magic byte
        if payload[0] != 0:
            raise ValueError("Invalid magic byte. Expected 0x00 for Confluent wire format")

        # Extract schema ID (4 bytes, big-endian)
        schema_id = struct.unpack('>I', payload[1:5])[0]

        # Get parsed schema
        parsed_schema = self._get_parsed_schema(schema_id)

        # Decode Avro data
        import io
        buf = io.BytesIO(payload[5:])
        data = fastavro.schemaless_reader(buf, parsed_schema)

        return schema_id, data

    def serialize_cloudevent(self, event: "CloudEvent", schema: Dict) -> bytes:
        """
        Serialize CloudEvent with Avro payload.

        Args:
            event: CloudEvent with data field
            schema: Avro schema for event.data

        Returns:
            Serialized event for Kafka (headers + binary value)
        """
        # Serialize the data payload
        subject = self._subject_from_event(event)
        value = self.serialize(subject, schema, event.data)

        return value

    def deserialize_cloudevent(self, headers: Dict[str, str], value: bytes) -> Tuple[Dict, Dict]:
        """
        Deserialize Kafka record to CloudEvent attributes + payload.

        Args:
            headers: Kafka record headers (Ce-* attributes)
            value: Binary value (Avro with schema ID)

        Returns:
            Tuple of (ce_attributes, decoded_payload)
        """
        # Extract CloudEvents attributes from headers
        ce_attrs = {}
        for k, v in headers.items():
            if k.lower().startswith("ce_"):
                attr = k[3:].replace("-", "_")
                ce_attrs[attr] = v

        # Deserialize Avro payload
        schema_id, payload = self.deserialize(value)

        return ce_attrs, payload

    def _subject_from_event(self, event: "CloudEvent") -> str:
        """Derive Schema Registry subject from CloudEvent type."""
        # Map event type to subject
        # e.g., "com.pdftranslator.catalog.work.created" -> "pdftranslator.catalog.work.created-value"
        event_type = event.type.replace("com.pdftranslator.", "")
        return f"pdftranslator.{event_type}-value"


# High-level convenience functions
def serialize_event(event: "CloudEvent", serializer: AvroSerializer, schema: Dict) -> bytes:
    """Serialize CloudEvent to Kafka-compatible binary."""
    return serializer.serialize_cloudevent(event, schema)


def deserialize_event(headers: Dict[str, str], value: bytes, serializer: AvroSerializer) -> Tuple["CloudEvent", Dict]:
    """Deserialize Kafka record to CloudEvent + payload."""
    ce_attrs, payload = serializer.deserialize_cloudevent(headers, value)

    # Reconstruct CloudEvent
    from .cloudevents import CloudEvent
    event = CloudEvent(
        specversion=ce_attrs.get("specversion", "1.0"),
        id=ce_attrs.get("id", ""),
        type=ce_attrs.get("type", ""),
        source=ce_attrs.get("source", ""),
        datacontenttype=ce_attrs.get("datacontenttype", "application/avro"),
        data=payload,
        subject=ce_attrs.get("subject"),
        time=ce_attrs.get("time"),
        traceparent=ce_attrs.get("traceparent"),
        tracestate=ce_attrs.get("tracestate"),
        extensions={k: v for k, v in ce_attrs.items() if k not in [
            "specversion", "id", "type", "source", "datacontenttype",
            "subject", "time", "traceparent", "tracestate"
        ]},
    )

    return event, payload


# Kafka Producer/Consumer Helpers
class EventProducer:
    """Kafka producer for CloudEvents with Avro serialization."""

    def __init__(
        self,
        bootstrap_servers: str,
        serializer: AvroSerializer,
        client_id: str = "pdftranslator-producer",
    ):
        from confluent_kafka import Producer

        self.producer = Producer({
            'bootstrap.servers': bootstrap_servers,
            'client.id': client_id,
            'acks': 'all',
            'linger.ms': 5,
            'compression.type': 'snappy',
        })
        self.serializer = serializer
        self._schemas: Dict[str, Dict] = {}  # event_type -> schema

    def register_schema(self, event_type: str, schema: Dict):
        """Register schema for event type."""
        self._schemas[event_type] = schema

    def produce(self, event: "CloudEvent", topic: Optional[str] = None, key: Optional[bytes] = None):
        """Produce CloudEvent to Kafka."""
        schema = self._schemas.get(event.type)
        if not schema:
            raise ValueError(f"No schema registered for event type: {event.type}")

        if topic is None:
            topic = self._topic_from_event(event)

        value = self.serializer.serialize_cloudevent(event, schema)
        headers = [(k, v.encode() if isinstance(v, str) else v) for k, v in event.to_http_headers().items()]

        self.producer.produce(topic, value=value, headers=headers, key=key)
        self.producer.poll(0)

    def flush(self, timeout: float = 10.0):
        """Flush pending messages."""
        self.producer.flush(timeout)

    def _topic_from_event(self, event: "CloudEvent") -> str:
        """Derive Kafka topic from event type."""
        # e.g., "com.pdftranslator.catalog.work.created" -> "pdftranslator.catalog.work.created"
        return event.type.replace("com.pdftranslator.", "pdftranslator.")


class EventConsumer:
    """Kafka consumer for CloudEvents with Avro deserialization."""

    def __init__(
        self,
        bootstrap_servers: str,
        group_id: str,
        serializer: AvroSerializer,
        topics: list[str],
        client_id: str = "pdftranslator-consumer",
    ):
        from confluent_kafka import Consumer

        self.consumer = Consumer({
            'bootstrap.servers': bootstrap_servers,
            'group.id': group_id,
            'client.id': client_id,
            'auto.offset.reset': 'earliest',
            'enable.auto.commit': False,
        })
        self.consumer.subscribe(topics)
        self.serializer = serializer

    def poll(self, timeout: float = 1.0) -> Optional[Tuple["CloudEvent", Dict]]:
        """Poll for next event."""
        msg = self.consumer.poll(timeout)
        if msg is None:
            return None
        if msg.error():
            raise RuntimeError(f"Kafka error: {msg.error()}")

        headers = dict(msg.headers()) if msg.headers() else {}
        value = msg.value()

        event, payload = deserialize_event(headers, value, self.serializer)
        return event, payload

    def commit(self):
        """Commit offsets."""
        self.consumer.commit()

    def close(self):
        """Close consumer."""
        self.consumer.close()