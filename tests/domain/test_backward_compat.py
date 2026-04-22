"""Tests that old import paths still work after domain migration."""


def test_core_models_work_import():
    from pdftranslator.core.models.work import Work, Volume, Chapter
    w = Work(id=1, title="Test")
    assert w.title == "Test"


def test_database_models_import():
    from pdftranslator.database.models import Work, Volume, Chapter, GlossaryEntry
    from pdftranslator.database.models import UploadedFile, SubstitutionRule
    from pdftranslator.database.models import EntityCandidate, BuildResult
    assert True


def test_glossary_entry_has_new_fields():
    from pdftranslator.database.models import GlossaryEntry
    entry = GlossaryEntry(notes="test", do_not_translate=True, is_verified=True, confidence=0.9)
    assert entry.notes == "test"
    assert entry.do_not_translate is True
