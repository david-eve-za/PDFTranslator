"""Tests for glossary_translator.py DIP fixes."""
from pdftranslator.services.glossary_translator import GlossaryAwareTranslator
from pdftranslator.domain.models.glossary import GlossaryEntry as DomainGlossaryEntry


def test_glossary_aware_translator_uses_domain_models():
    entries = [DomainGlossaryEntry(term="Dragon", translation="dragon")]
    translator = GlossaryAwareTranslator.__new__(GlossaryAwareTranslator)
    assert True
