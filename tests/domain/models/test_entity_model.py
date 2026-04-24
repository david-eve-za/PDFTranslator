"""Tests for domain entity models."""
from pdftranslator.domain.models.entity import EntityCandidate, GlossaryBuildProgress


def test_entity_candidate_add_context():
    e = EntityCandidate(text="Dragon")
    e.add_context("The dragon flew over the mountains.")
    e.add_context("The dragon flew over the mountains.")
    assert len(e.contexts) == 1


def test_entity_candidate_best_context():
    e = EntityCandidate(text="Dragon", contexts=["ctx1", "ctx2"])
    assert e.best_context() == "ctx1"


def test_glossary_build_progress_next_phase():
    p = GlossaryBuildProgress(phase="extracted")
    assert p.next_phase() == "validated"
    assert p.is_complete() is False


def test_glossary_build_progress_is_complete():
    p = GlossaryBuildProgress(phase="saved")
    assert p.is_complete() is True
