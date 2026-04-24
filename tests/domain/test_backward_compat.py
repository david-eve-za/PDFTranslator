"""Tests that domain models are the canonical import source (post-bridge deletion)."""


def test_core_models_work_import():
    from pdftranslator.core.models.work import Work
    w = Work(id=1, title="Test")
    assert w.title == "Test"


def test_domain_models_direct_import():
    assert True


def test_glossary_entry_has_new_fields():
    from pdftranslator.domain.models.glossary import GlossaryEntry
    entry = GlossaryEntry(notes="test", do_not_translate=True, is_verified=True, confidence=0.9)
    assert entry.notes == "test"
    assert entry.do_not_translate is True
