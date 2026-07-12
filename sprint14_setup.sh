#!/usr/bin/env bash
# Sprint 1.4: Event Schemas (CloudEvents + Avro)
# Run this script to create the feature branch and setup directory structure

set -euo pipefail

echo "=== Sprint 1.4: Event Schemas (CloudEvents + Avro) ==="
echo ""

# Ensure we're on main and up to date
echo "📍 Switching to main and pulling latest..."
git checkout main
git pull origin main

# Create feature branch
echo "🌿 Creating feature branch..."
git checkout -b chore/event-schemas-cloud-events

echo "✅ Branch 'chore/event-schemas-cloud-events' created"
echo ""

# Create directory structure
echo "📁 Creating directory structure..."
mkdir -p docs/events/schemas/avro
mkdir -p docs/events/schemas/cloudevents
mkdir -p docs/events/registry
mkdir -p src/pdftranslator/shared/events/{python,go,typescript}

echo "✅ Directory structure created"
echo ""

# Show structure
echo "📂 Event schemas directory layout:"
tree docs/events/ 2>/dev/null || find docs/events -type f | sort

echo ""
echo "🎯 Next steps (manual):"
echo "   1. Define Avro schemas in docs/events/schemas/avro/"
echo "   2. Define CloudEvents specs in docs/events/schemas/cloudevents/"
echo "   3. Configure Schema Registry in docs/events/registry/"
echo "   4. Generate client code in src/pdftranslator/shared/events/"
echo "   5. Write tests and documentation"
echo "   6. Commit and merge to main"
echo "   7. Tag v0.4.0 and update CHANGELOG.md"