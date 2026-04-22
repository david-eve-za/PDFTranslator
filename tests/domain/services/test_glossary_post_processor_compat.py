"""Tests that GlossaryPostProcessor is importable from domain."""
from pdftranslator.domain.services.glossary_post_processor import GlossaryPostProcessor as DomainProcessor
from pdftranslator.cli.services.glossary_post_processor import GlossaryPostProcessor as CliProcessor
from pdftranslator.database.models import GlossaryEntry


def test_domain_processor_same_interface():
    entries = [GlossaryEntry(term="Dragon", translation="dragon")]
    processor = DomainProcessor(entries, "es")
    assert processor is not None


def test_cli_processor_reexports_domain():
    assert CliProcessor is DomainProcessor
