#!/usr/bin/env bash
# Sprint 1.4: Event Schemas (CloudEvents + Avro)
# Run this script to create the feature branch

set -e

echo "=== Sprint 1.4: Event Schemas (CloudEvents + Avro) ==="
echo ""
echo "Creating feature branch from main..."

# Ensure we're on main and up to date
git checkout main
git pull origin main

# Create feature branch
git checkout -b chore/event-schemas-cloud-events

echo ""
echo "✅ Branch 'chore/event-schemas-cloud-events' created"
echo ""
echo "Next steps:"
echo "1. Create event schemas directory structure"
echo "2. Define Avro schemas for core events"
echo "3. Add CloudEvents envelope specifications"
echo "4. Configure Schema Registry (Apicurio/Confluent)"
echo "5. Generate client code for Python/Go/TypeScript"
echo "6. Document versioning strategy"
echo "7. Run tests and commit"
echo "8. Merge to main with tag v0.4.0"