# CloudEvents Envelope Specification for PDFTranslator

## Overview
All events in the PDFTranslator ecosystem are wrapped in a CloudEvents 1.0 envelope. This document specifies the required attributes, extension attributes, and serialization format.

## Required CloudEvents Attributes

| Attribute | Required | Type | Description |
|-----------|----------|------|-------------|
| `specversion` | ✅ | string | Must be `"1.0"` |
| `type` | ✅ | string | Event type URI (e.g., `com.pdftranslator.catalog.work.created`) |
| `source` | ✅ | string | Source service URI (e.g., `/pdftranslator/catalog-service`) |
| `id` | ✅ | string | Unique event ID (UUID v4) |
| `time` | ✅ | string | RFC3339 timestamp (e.g., `2024-01-15T10:30:00.123Z`) |
| `datacontenttype` | ✅ | string | Must be `"application/avro"` |

## Extension Attributes (PDFTranslator Specific)

| Attribute | Required | Type | Description |
|-----------|----------|------|-------------|
| `eventversion` | ✅ | integer | Schema version number (default: 1) |
| `traceid` | ❌ | string | W3C traceparent trace-id |
| `spanid` | ❌ | string | W3C traceparent span-id |
| `traceflags` | ❌ | string | W3C trace-flags (e.g., `01` for sampled) |

## Event Type Naming Convention

```
com.pdftranslator.{service}.{entity}.{action}
```

| Service | Domain | Entity | Actions |
|---------|--------|--------|---------|
| `catalog` | Metadata | `work`, `volume`, `chapter` | `created`, `updated`, `deleted` |
| `document` | Extraction | `document` | `extracted`, `failed` |
| `glossary` | Terminology | `glossary` | `built`, `updated`, `deleted` |
| `translation` | Translation | `job`, `segment` | `queued`, `started`, `completed`, `failed`, `paused`, `resumed`, `cancelled` |
| `job` | Orchestration | `workflow` | `started`, `completed`, `failed`, `step_completed` |
| `audio` | TTS | `audiobook` | `generated`, `failed` |

## Example CloudEvents Envelope (JSON Mode)

```json
{
  "specversion": "1.0",
  "type": "com.pdftranslator.catalog.work.created",
  "source": "/pdftranslator/catalog-service",
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "time": "2024-01-15T10:30:00.123Z",
  "datacontenttype": "application/avro",
  "eventversion": 1,
  "traceid": "4bf92f3577b34da6a3ce929d0e0e4736",
  "spanid": "00f067aa0ba902b7",
  "traceflags": "01",
  "data_base64": "CgAKB...Avro binary encoded payload..."
}
```

## Serialization Modes

### 1. Binary Mode (Recommended for Kafka)
- CloudEvents attributes as **Kafka record headers**
- Avro binary payload as **record value**
- Schema ID embedded in payload (Confluent wire format)

```
Headers:
  ce_specversion: "1.0"
  ce_type: "com.pdftranslator.catalog.work.created"
  ce_source: "/pdftranslator/catalog-service"
  ce_id: "550e8400-e29b-41d4-a716-446655440000"
  ce_time: "2024-01-15T10:30:00.123Z"
  ce_datacontenttype: "application/avro"
  ce_eventversion: "1"
  ce_traceid: "4bf92f3577b34da6a3ce929d0e0e4736"
  ce_spanid: "00f067aa0ba902b7"

Value: [Schema ID byte][Avro binary payload]
```

### 2. Structured Mode (HTTP/REST)
- Full CloudEvents envelope as JSON
- Base64-encoded Avro payload in `data_base64` field

```json
{
  "specversion": "1.0",
  "type": "com.pdftranslator.catalog.work.created",
  "source": "/pdftranslator/catalog-service",
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "time": "2024-01-15T10:30:00.123Z",
  "datacontenttype": "application/avro",
  "eventversion": 1,
  "data_base64": "CgAKB...base64 encoded avro..."
}
```

### 3. Batch Mode (HTTP/Webhooks)
- Array of CloudEvents for bulk delivery

```json
[
  {"specversion": "1.0", "type": "...", ...},
  {"specversion": "1.0", "type": "...", ...}
]
```

## Avro Schema Registration

All Avro schemas are registered in **Schema Registry** with subjects:
```
{pdftranslator}.{service}.{entity}.{action}-value
```

Examples:
- `pdftranslator.catalog.work.created-value`
- `pdftranslator.translation.job.completed-value`
- `pdftranslator.glossary.glossary.built-value`

## Versioning Policy

| Change Type | Compatibility | Version Bump |
|-------------|---------------|--------------|
| Add optional field with default | BACKWARD | Minor (v1→v2) |
| Add required field | NONE (breaking) | Major (v1→v2 with migration) |
| Remove optional field | FORWARD | Minor |
| Change field type | NONE (breaking) | Major |
| Rename field | NONE (breaking) | Major |

**Rule**: Default compatibility is **BACKWARD** (consumers can read new schemas with old code)

## Error Events

Error events follow the same envelope but with:
- `type`: `com.pdftranslator.{service}.error`
- `datacontenttype`: `application/json`
- Payload: Structured error with `error_code`, `message`, `details`

```json
{
  "specversion": "1.0",
  "type": "com.pdftranslator.translation.error",
  "source": "/pdftranslator/translation-service",
  "id": "err-550e8400-e29b-41d4-a716-446655440000",
  "time": "2024-01-15T10:30:00.123Z",
  "datacontenttype": "application/json",
  "data": {
    "error_code": "TRANSLATION_RATE_LIMITED",
    "message": "NVIDIA NIM rate limit exceeded",
    "details": {
      "retry_after_seconds": 60,
      "job_id": "job-123",
      "provider": "nvidia"
    }
  }
}
```

## Implementation Libraries

| Language | Library | Version |
|----------|---------|---------|
| Python | `cloudevents` + `fastavro` | ≥1.0 |
| Go | `cloudevents/sdk-go` + `linkedin/goavro` | ≥2.0 |
| TypeScript | `cloudevents` + `avsc` | ≥1.0 |
| Rust | `cloudevents` + `apache-avro` | ≥0.4 |

## Validation Checklist for New Events

- [ ] Event type follows naming convention
- [ ] Avro schema defined in `docs/events/schemas/avro/`
- [ ] CloudEvents metadata in Avro file matches spec
- [ ] Schema registered in Schema Registry
- [ ] Client code generated for all target languages
- [ ] Compatibility test passes (BACKWARD)
- [ ] Documentation updated with example payload