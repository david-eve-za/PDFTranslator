# Schema Registry Configuration

## Apicurio Registry (Recommended for Open Source)

### Deployment (Docker Compose)
```yaml
# docker-compose.registry.yml
version: '3.8'
services:
  apicurio-registry:
    image: apicurio/apicurio-registry-mem:2.5.0
    ports:
      - "8080:8080"
    environment:
      REGISTRY_KAFKA_BOOTSTRAP: "kafka:9092"
      REGISTRY_KAFKA_TOPIC: "__schemas"
      REGISTRY_STORAGE: "memory"
```

### Production (PostgreSQL Backend)
```yaml
# docker-compose.registry.prod.yml
services:
  apicurio-registry:
    image: apicurio/apicurio-registry-jpa:2.5.0
    environment:
      REGISTRY_DATASOURCE_URL: "jdbc:postgresql://postgres:5432/registry"
      REGISTRY_DATASOURCE_USERNAME: "registry"
      REGISTRY_DATASOURCE_PASSWORD_FILE: "/run/secrets/registry_password"
      REGISTRY_KAFKA_BOOTSTRAP: "kafka:9092"
```

## Confluent Schema Registry (Enterprise)

```yaml
# docker-compose.schema-registry.yml
services:
  schema-registry:
    image: confluentinc/cp-schema-registry:7.5.0
    ports:
      - "8081:8081"
    environment:
      SCHEMA_REGISTRY_HOST_NAME: schema-registry
      SCHEMA_REGISTRY_KAFKASTORE_BOOTSTRAP_SERVERS: "kafka:9092"
      SCHEMA_REGISTRY_LISTENERS: "http://0.0.0.0:8081"
      SCHEMA_REGISTRY_COMPATIBILITY: "BACKWARD"
```

## Subject Naming Strategy

```properties
# schema-registry.properties
schema.registry.url=http://localhost:8081
# Subject format: {topic}-value for Avro values, {topic}-key for keys
# Our convention: pdftranslator.{service}.{entity}.{action}-value

# Default compatibility level
compatibility.level=BACKWARD
```

## Schema Registration Scripts

### Register All Schemas (Apicurio)
```bash
#!/bin/bash
# register-schemas-apicurio.sh

REGISTRY_URL="http://localhost:8080/apis/registry/v2"
GROUP="pdftranslator"

for schema in docs/events/schemas/avro/*.avsc; do
    name=$(basename "$schema" .avsc)
    subject="pdftranslator.$name-value"
    
    echo "Registering $subject..."
    curl -X POST "$REGISTRY_URL/groups/$GROUP/artifacts" \
      -H "Content-Type: application/json" \
      -H "X-Registry-ArtifactId: $subject" \
      -d @"$schema"
done
```

### Register All Schemas (Confluent)
```bash
#!/bin/bash
# register-schemas-confluent.sh

REGISTRY_URL="http://localhost:8081"
GROUP="pdftranslator"

for schema in docs/events/schemas/avro/*.avsc; do
    name=$(basename "$schema" .avsc)
    subject="pdftranslator.$name-value"
    
    echo "Registering $subject..."
    curl -X POST "$REGISTRY_URL/subjects/$subject/versions" \
      -H "Content-Type: application/vnd.schemaregistry.v1+json" \
      -d "{\"schema\": $(jq -Rs . < "$schema")}"
done
```

## Compatibility Checks

```bash
# Check compatibility before registering new version
curl -X POST "$REGISTRY_URL/compatibility/subjects/pdftranslator.work.created-value/versions" \
  -H "Content-Type: application/vnd.schemaregistry.v1+json" \
  -d '{"schema": "..."}'

# Response: {"is_compatible": true}
```

## Migration Strategy

| Phase | Action |
|-------|--------|
| 1 | Deploy Schema Registry alongside existing system |
| 2 | Register all current schemas (v1) |
| 3 | Enable schema validation on producers |
| 4 | Migrate consumers to use schema registry |
| 5 | Enable BACKWARD compatibility enforcement |
| 6 | Begin schema evolution with versioned changes |

## Monitoring

### Key Metrics
- `schema_registry.schema.count` - Total schemas registered
- `schema_registry.schema.subject.count` - Unique subjects
- `schema_registry.request.latency` - API latency
- `schema_registry.errors.total` - Registration/validation errors

### Alerts
- Schema registration failures > 0 in 5min
- Compatibility check failures > 0
- Registry unavailable > 1min

## Client Configuration

### Python (Apicurio)
```python
from apicurio_client import ApicurioRegistryClient

client = ApicurioRegistryClient(
    registry_url="http://localhost:8080/apis/registry/v2",
    group_id="pdftranslator"
)

# Register schema
artifact_id = "pdftranslator.work.created-value"
schema = open("docs/events/schemas/avro/work_created.avsc").read()
client.create_artifact(artifact_id, schema, "AVRO")

# Get schema by ID
schema = client.get_artifact_by_id(artifact_id, version=1)
```

### Python (Confluent)
```python
from schema_registry.client import SchemaRegistryClient

client = SchemaRegistryClient(url="http://localhost:8081")

# Register
subject = "pdftranslator.work.created-value"
schema = open("docs/events/schemas/avro/work_created.avsc").read()
schema_id = client.register(subject, schema)

# Serialize with schema ID
from confluent_kafka.schema_registry import SchemaRegistryClient
from confluent_kafka.schema_registry.avro import AvroSerializer

serializer = AvroSerializer(client, schema_str, to_dict_func)
```

### Go (Confluent)
```go
import (
    "github.com/confluentinc/confluent-kafka-go/v2/kafka"
    "github.com/confluentinc/confluent-kafka-go/v2/schemaregistry"
    "github.com/confluentinc/confluent-kafka-go/v2/schemaregistry/serde/avro"
)

client, _ := schemaregistry.NewClient(schemaregistry.NewConfig("http://localhost:8081"))
serializer, _ := avro.NewSerializer(client, avro.NewSerializerConfig())
```

### TypeScript (Confluent)
```typescript
import { SchemaRegistry } from '@confluentinc/schemaregistry';
import { AvroSerializer } from '@confluentinc/kafka-avro-serializer';

const registry = new SchemaRegistry({ host: 'http://localhost:8081' });
const serializer = new AvroSerializer(registry, schema);
```

## Schema Evolution Guidelines

### ✅ Safe Changes (BACKWARD compatible)
- Add optional field with default
- Add field with default value
- Remove optional field (consumers ignore)
- Reorder fields
- Add enum symbol (consumers handle unknown)

### ❌ Breaking Changes (require Major version)
- Remove required field
- Change field type (int → string)
- Remove enum symbol used by consumers
- Rename field
- Change field nullability (required → optional OK, optional → required NOT OK)

### Migration Pattern for Breaking Changes
1. Register new schema as `subject-v2` (new subject)
2. Run dual-write period (produce to both)
3. Migrate all consumers to v2
4. Retire v1 subject after grace period

## Backup/Restore

```bash
# Export all schemas
curl -s "http://localhost:8081/subjects" | jq -r '.[]' | while read subject; do
    curl -s "http://localhost:8081/subjects/$subject/versions/latest" | \
    jq -r '.schema' | jq . > "backup/$subject.avsc"
done

# Restore
for schema in backup/*.avsc; do
    subject=$(basename "$schema" .avsc)
    curl -X POST "http://localhost:8081/subjects/$subject/versions" \
      -H "Content-Type: application/vnd.schemaregistry.v1+json" \
      -d "{\"schema\": $(jq -Rs . < "$schema")}"
done
```