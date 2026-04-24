"""Tests for glossary_translator.py DIP fixes."""
from pdftranslator.domain.models.glossary import GlossaryEntry as DomainGlossaryEntry
from pdftranslator.services.glossary_translator import GlossaryAwareTranslator


def test_glossary_aware_translator_uses_domain_models():

    entries = [DomainGlossaryEntry(term="Dragon", translation="dragón")]
    mock_translator = None
    _ = GlossaryAwareTranslator(translator=mock_translator, glossary_entries=entries)
    assert isinstance(entries[0], DomainGlossaryEntry)
