#!/usr/bin/env bash
# Refactoring validation metrics script
# Usage: ./scripts/refactor_metrics.sh

set -e
echo "=== PDFTranslator Refactoring Metrics ==="
echo ""

echo "--- Tests ---"
python -m pytest tests/cli/ tests/backend/ tests/integration/ --tb=short -q "$@" 2>&1 | tail -5
echo ""

echo "--- Coverage ---"
python -m pytest tests/cli/ tests/backend/ tests/integration/ --cov=src/pdftranslator --cov-report=term-missing --tb=short -q "$@" 2>&1 | tail -10 || echo "Coverage not available"
echo ""

echo "--- Lint ---"
python -m ruff check src/ 2>&1 | tail -5 || echo "Ruff not available"
echo ""

echo "--- Import Check ---"
python -c "import pdftranslator; print('Import OK')" 2>&1 || echo "Import FAILED"
echo ""

echo "--- Circular Import Check ---"
python -c "
from pdftranslator.core.config.settings import Settings
from pdftranslator.database.connection import DatabasePool
from pdftranslator.infrastructure.llm.factory import LLMFactory
from pdftranslator.services.translator import TranslatorService
print('No circular imports detected')
" 2>&1 || echo "Circular import DETECTED"
