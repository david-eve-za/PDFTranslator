"""Tests for domain glossary models."""
from pdftranslator.domain.models.glossary import (
    ContextExample,
    GlossaryEntry,
    TermContext,
)


def test_glossary_entry_has_new_sql_columns():
    entry = GlossaryEntry(
        id=1, work_id=1, term="Dragon",
        notes="Important entity", do_not_translate=True,
        is_verified=True, confidence=0.95,
    )
    assert entry.notes == "Important entity"
    assert entry.do_not_translate is True
    assert entry.is_verified is True
    assert entry.confidence == 0.95


def test_term_context_has_examples_field():
    example = ContextExample(original_sentence="The dragon flew.", translated_sentence="El dragon volo.")
    ctx = TermContext(context_hint="Mythical creature", translation="dragon", examples=[example])
    assert len(ctx.examples) == 1
