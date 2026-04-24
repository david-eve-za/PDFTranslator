"""Tests for domain work models."""
from pdftranslator.domain.models.work import Chapter, Volume, Work


def test_work_dataclass_exists():
    work = Work(id=1, title="Test Book")
    assert work.title == "Test Book"
    assert work.id == 1


def test_volume_dataclass_exists():
    volume = Volume(id=1, work_id=1, volume_number=1)
    assert volume.volume_number == 1
    assert volume.glossary_build_status == "pending"


def test_chapter_dataclass_nullable_number():
    chapter = Chapter(id=1, volume_id=1, chapter_number=None, title="Prologue")
    assert chapter.chapter_number is None


def test_chapter_dataclass_numbered():
    chapter = Chapter(id=1, volume_id=1, chapter_number=5, title="Chapter 5")
    assert chapter.chapter_number == 5
