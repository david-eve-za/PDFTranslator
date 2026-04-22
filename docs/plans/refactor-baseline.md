# Refactoring Baseline Metrics

**Date:** 2026-04-22
**Tag:** refactor-safe-point

## Test Results

**Working tests (tests/cli/, tests/backend/, tests/integration/):**
- 25 passed, 10 failed, 0 errors

**Full test suite (114 collected):**
- 18 collection errors (tests using old import paths like `from config.` instead of `from pdftranslator.config.`)
- 10 test failures in `tests/cli/test_glossary_post_processor.py` (GlossaryEntry constructor mismatch — `source_term` kwarg)
- 1 test failure in `tests/test_no_config_json.py` (timeout)

**Collection errors are from these test files using legacy imports:**
- tests/config/test_document.py (`from config.document`)
- tests/database/test_base_repository.py (`from database.repositories.base`)
- tests/database/test_chapter_repository.py (`from database.repositories.chapter_repository`)
- tests/database/test_connection.py (`from database.connection`)
- tests/database/test_entity_blacklist_repository.py
- tests/database/test_entity_extractor.py
- tests/database/test_exceptions.py (`from database.exceptions`)
- tests/database/test_fantasy_term_repository.py
- tests/database/test_glossary_repository.py
- tests/database/test_integration_initializer.py
- tests/infrastructure/document/test_docling_extractor.py (`from infrastructure.document`)
- tests/infrastructure/document/test_section_grouper.py
- tests/test_document_chapter_splitter_v2.py (`from document_chapter_splitter_v2`)
- tests/test_integration_docling.py
- tests/test_nvidia_ai.py (`from llm.nvidia_llm`)
- tests/test_section_classifier_enhanced.py
- tests/test_section_classifier_integration.py
- tests/test_simplified_text_extractor.py (`from tools.TextExtractor`)

## Coverage

**Overall: 29% (5089 statements, 3299 missed, 1168 excluded)**
**10 failed, 25 passed**

Key coverage areas:
- core/config: 80-100%
- database/repositories: 55-93%
- database/services: 42-95%
- infrastructure/llm: 25-67%
- services: 26-48%
- tools: 12-42%

## Known Issues
- 18 test files use legacy import paths (not `pdftranslator.` prefix)
- GlossaryEntry constructor uses `source_term` kwarg which doesn't exist on current model
- test_no_config_json.py times out (PDFAgent.py subprocess)
- Coverage tool is configured but many tests can't run due to import errors
- Some tests require NVIDIA_API_KEY (skipped)
- Some tests require database (integration)
