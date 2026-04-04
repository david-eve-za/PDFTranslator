# Test Fixtures

This directory contains test documents for document processing tests.

## Documents

Due to file size, actual PDF/DOCX files are not committed to git.

For testing, you can:
1. Use any small PDF/DOCX file
2. Create test documents programmatically
3. Use mock objects in unit tests

## Integration Tests

Integration tests that require real documents should:
1. Skip if fixture not found
2. Use `@pytest.mark.integration` marker
