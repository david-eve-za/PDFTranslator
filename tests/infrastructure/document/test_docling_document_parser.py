"""Tests for DoclingDocumentParser adapter."""
from pdftranslator.domain.protocols.document_parser import DocumentParser
from pdftranslator.infrastructure.document.docling_document_parser import DoclingDocumentParser


def test_docling_parser_satisfies_protocol():
    parser = DoclingDocumentParser.__new__(DoclingDocumentParser)
    assert isinstance(parser, DocumentParser)


def test_docling_parser_supported_extensions():
    parser = DoclingDocumentParser.__new__(DoclingDocumentParser)
    assert ".pdf" in parser.supported_extensions
    assert ".epub" in parser.supported_extensions
