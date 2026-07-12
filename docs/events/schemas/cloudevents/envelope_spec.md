# CloudEvents 1.0 Envelope Specification for PDFTranslator

## Overview
All events in the PDFTranslator ecosystem follow the **CloudEvents 1.0 specification** with Avro-encoded payloads. This ensures:
- **Interoperability**: Standard envelope understood by all consumers
- **Observability**: Trace context propagation via `traceparent` headers
- **Schema Evolution**: Avro schemas registered in Schema Registry with compatibility rules
- **Routing**: Content-based routing via `type` and `source` attributes

## CloudEvents Envelope Structure

```json
{
  "specversion": "1.0",
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "type": "com.pdftranslator.catalog.work.created",
  "source": "/pdftranslator/catalog-service",
  "datacontenttype": "application/avro",
  "data": "<avro-binary-payload>",
  "subject": "work/550e8400-e29b-41d4-a716-446655440000",
  "time": "2026-07-12T10:30:00Z",
  "traceparent": "00-0af7651916cd43dd8448eb211c80319c-b7ad6b7169203331-01",
  "extensions": {
    "eventversion": 1,
    "correlationid": "job-12345"
  }
}
```

## Required CloudEvents Attributes

| Attribute | Required | Description | PDFTranslator Convention |
|-----------|----------|-------------|-------------------------|
| `specversion` | ✅ | CloudEvents spec version | Always `"1.0"` |
| `id` | ✅ | Unique event ID | UUID v4 (RFC 4122) |
| `type` | ✅ | Event type identifier | `com.pdftranslator.<domain>.<action>` |
| `source` | ✅ | Event producer URI | `/pdftranslator/<service-name>` |
| `datacontenttype` | ✅ | Data encoding format | `"application/avro"` |

## Optional But Recommended Attributes

| Attribute | Description | PDFTranslator Convention |
|-----------|-------------|-------------------------|
| `subject` | Resource identifier | `<resource-type>/<resource-uuid>` (e.g., `work/uuid`, `job/uuid`) |
| `time` | Event timestamp (RFC 3339) | UTC timestamp when event occurred |
| `traceparent` | W3C trace context | Propagated from incoming request or generated |
| `tracestate` | Vendor-specific trace state | Optional, for vendor extensions |

## Extension Attributes (Custom)

| Extension | Type | Description |
|-----------|------|-------------|
| `eventversion` | int | Avro schema version of the `data` payload |
| `correlationid` | string | Business correlation ID (e.g., job ID, work ID) |
| `causationid` | string | ID of the event that caused this event |
| `partitionkey` | string | Kafka partition key for ordering |

## Event Type Naming Convention

```
com.pdftranslator.<service-domain>.<resource>.<action>
```

### Service Domains
| Domain | Service | Examples |
|--------|---------|----------|
| `catalog` | Catalog Service | `work.created`, `volume.created`, `chapter.updated` |
| `document` | Document Service | `extracted`, `failed` |
| `glossary` | Glossary Service | `built`, `updated`, `validated` |
| `translation` | Translation Service | `job.queued`, `job.started`, `job.completed`, `job.failed` |
| `job` | Job Orchestrator | `status.changed`, `workflow.started`, `workflow.completed` |
| `audio` | Audio Service | `generated`, `failed` |

### Actions
| Action | Semantics |
|--------|-----------|
| `created` | Resource created |
| `updated` | Resource modified |
| `deleted` | Resource deleted |
| `extracted` | Document extraction complete |
| `built` | Glossary/build artifact complete |
| `queued` | Job queued for processing |
| `started` | Job/processing started |
| `completed` | Job completed successfully |
| `failed` | Job/processing failed |
| `status.changed` | State transition |

## Event Versioning Strategy

### Avro Schema Versioning
- **Rule**: `BACKWARD` compatibility (new schema can read old data)
- **Field Addition**: Optional fields with defaults only
- **Field Removal**: Never remove fields; mark as deprecated
- **Type Changes**: Not allowed (would break consumers)
- **Enum Additions**: Allowed with `default` symbol

### CloudEvents `eventversion` Extension
Each event includes `eventversion` extension indicating the Avro schema version:
```json
{
  "extensions": {
    "eventversion": 2
  }
}
```

### Semantic Versioning for Event Types
| Version | Meaning |
|---------|---------|
| v1 | Initial release |
| v1.1 | Backward-compatible field additions |
| v2.0 | Breaking changes (new event type with versioned name) |

For breaking changes, create **new event type**: `com.pdftranslator.catalog.work.created.v2`

## Transport Bindings

### Kafka Binding (Primary)
```properties
# Key: subject (e.g., "work/550e8400-...")
# Value: CloudEvents JSON with binary Avro data
# Headers:
#   ce_specversion: "1.0"
#   ce_id: "uuid"
#   ce_type: "com.pdftranslator.catalog.work.created"
#   ce_source: "/pdftranslator/catalog-service"
#   ce_datacontenttype: "application/avro"
#   ce_subject: "work/uuid"
#   ce_time: "2026-07-12T10:30:00Z"
#   traceparent: "00-...-...-01"
#   eventversion: "1"
```

### HTTP Binding (Webhooks/Callbacks)
```http
POST /webhooks/events
Content-Type: application/cloudevents+json
Ce-Specversion: 1.0
Ce-Id: 550e8400-e29b-41d4-a716-446655440000
Ce-Type: com.pdftranslator.catalog.work.created
Ce-Source: /pdftranslator/catalog-service
Ce-Datacontenttype: application/avro
Ce-Subject: work/550e8400-e29b-41d4-a716-446655440000
Ce-Time: 2026-07-12T10:30:00Z
Traceparent: 00-0af7651916cd43dd8448eb211c80319c-b7ad6b7169203331-01
Eventversion: 1

<avro-binary-payload>
```

### NATS Binding (Future)
Subject pattern: `pdftranslator.catalog.work.created.work.<uuid>`

## Schema Registry Integration

### Confluent Schema Registry / Apicurio
- **Subject Naming**: `<event-type>-value` (e.g., `com.pdftranslator.catalog.work.created-value`)
- **Compatibility**: `BACKWARD` (default)
- **Validation**: Enforce on produce/consume
- **Retention**: Keep all versions indefinitely

### Avro Schema Registration
```bash
# Register schema
curl -X POST http://schema-registry:8081/subjects/com.pdftranslator.catalog.work.created-value/versions \
  -H "Content-Type: application/vnd.schemaregistry.v1+json" \
  -d '{"schema": "<escaped-avro-schema-json>"}'

# Check compatibility
curl -X POST http://schema-registry:8081/compatibility/subjects/com.pdftranslator.catalog.work.created-value/versions/latest \
  -H "Content-Type: application/vnd.schemaregistry.v1+json" \
  -d '{"schema": "<escaped-avro-schema-json>"}'
```

## Error Event Pattern

For failed operations, emit a dedicated event:

```json
{
  "specversion": "1.0",
  "id": "uuid",
  "type": "com.pdftranslator.translation.job.failed",
  "source": "/pdftranslator/translation-service",
  "datacontenttype": "application/avro",
  "subject": "job/job-uuid",
  "time": "2026-07-12T10:35:00Z",
  "traceparent": "00-...-...-01",
  "extensions": {
    "eventversion": 1,
    "correlationid": "job-12345",
    "errorcode": "LLM_RATE_LIMIT"
  }
}
```

## Consumer Implementation Guidelines

### Python Consumer
```python
from cloudevents.http import from_http
from pdftranslator.shared.events import deserialize_event

async def handle_event(request: Request):
    # Parse CloudEvents from HTTP
    event = from_http(request.headers, await request.body())
    
    # Deserialize Avro payload using schema registry
    payload = await deserialize_event(event)
    
    # Handle based on type
    if event["type"] == "com.pdftranslator.catalog.work.created":
        await handle_work_created(payload)
```

### Go Consumer
```go
func handleEvent(ctx context.Context, msg *ConsumerMessage) error {
    // Parse CloudEvents headers
    event := cloudevents.NewEvent()
    if err := event.UnmarshalBinary(msg.Value); err != nil {
        return err
    }
    
    // Deserialize Avro
    var payload WorkCreatedPayload
    if err := schemaRegistry.Deserialize(event.Data(), &payload); err != nil {
        return err
    }
    
    // Route by type
    switch event.Type() {
    case "com.pdftranslator.catalog.work.created":
        return handleWorkCreated(ctx, payload)
    }
    return nil
}
```

## Testing CloudEvents

### Contract Test Example (Pact)
```yaml
# pact/contracts/cloudevents.json
{
  "consumer": "translation-service",
  "provider": "catalog-service",
  "interactions": [{
    "description": "WorkCreated event",
    "request": {
      "method": "POST",
      "path": "/webhooks/events",
      "headers": {
        "Ce-Type": "com.pdftranslator.catalog.work.created",
        "Ce-Specversion": "1.0"
      },
      "body": {
        "event_id": "like(uuid)",
        "payload": {
          "work_id": "like(uuid)",
          "title": "like(string)",
          "source_lang": "like('en')",
          "target_lang": "like('es')"
        }
      }
    },
    "response": {"status": 200}
  }]
}
```

## References
- [CloudEvents 1.0 Spec](https://github.com/cloudevents/spec/blob/v1.0/spec.md)
- [Avro Specification](https://avro.apache.org/docs/current/spec.html)
- [Confluent Schema Registry](https://docs.confluent.io/platform/current/schema-registry/index.html)
- [W3C Trace Context](https://www.w3.org/TR/trace-context/)