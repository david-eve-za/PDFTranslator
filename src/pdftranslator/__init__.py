"""
PDFTranslator - AI-powered PDF/EPUB document translation with glossary management.

This package provides tools for translating PDF and EPUB documents using
LLM backends (NVIDIA NIM, Gemini, Ollama) with intelligent glossary management
using PostgreSQL and pgvector.

Example usage:
    # Using CLI
    pdftranslator cli translate document.pdf

    # Using Python
    from pdftranslator.core.config.settings import Settings
    from pdftranslator.services.translator import TranslatorService
"""

__version__ = "0.2.0"
__author__ = "David Gonzalez"
__email__ = "david@example.com"

__all__ = [
    "__version__",
    "__author__",
    "__email__",
]
