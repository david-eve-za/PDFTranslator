"""Tests for GlossaryBuildOrchestrator."""
from unittest.mock import MagicMock
from pdftranslator.application.services.glossary_build_orchestrator import GlossaryBuildOrchestrator
from pdftranslator.domain.protocols.llm import TextGenerator
from pdftranslator.domain.protocols.embedding import EmbeddingProvider
from pdftranslator.domain.protocols.repositories import GlossaryProgressTracker


def test_glossary_build_orchestrator_constructor():
    mock_llm = MagicMock(spec=TextGenerator)
    mock_embedder = MagicMock(spec=EmbeddingProvider)
    mock_embedder.embed_documents.return_value = [[0.1, 0.2]]
    mock_tracker = MagicMock(spec=GlossaryProgressTracker)
    mock_glossary_repo = MagicMock()
    mock_extractor = MagicMock()
    mock_extractor.extract.return_value = []

    orchestrator = GlossaryBuildOrchestrator(
        llm_client=mock_llm,
        embedder=mock_embedder,
        progress_tracker=mock_tracker,
        glossary_repo=mock_glossary_repo,
        entity_extractor=mock_extractor,
        max_output_tokens=4096,
    )
    assert orchestrator is not None
