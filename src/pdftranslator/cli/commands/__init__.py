# cli/commands/__init__.py
"""
CLI commands package for PDFTranslator.

This package contains all CLI commands that can be invoked through the typer app.
"""

from pdftranslator.cli.commands.process import process
from pdftranslator.cli.commands.add_to_database import add_to_database
from pdftranslator.cli.commands.split_text import split_text
from pdftranslator.cli.commands.reset_database import reset_database
from pdftranslator.cli.commands.build_glossary import build_glossary
from pdftranslator.cli.commands.translate_chapter import translate_chapter

__all__ = [
    "process",
    "add_to_database",
    "split_text",
    "reset_database",
    "build_glossary",
    "translate_chapter",
]
