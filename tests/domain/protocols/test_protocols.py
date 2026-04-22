"""Tests for all domain protocols."""
from pdftranslator.domain.protocols.embedding import EmbeddingProvider
from pdftranslator.domain.protocols.reranking import RerankingProvider
from pdftranslator.domain.protocols.audio_synthesizer import AudioSynthesizer
from pdftranslator.domain.protocols.document_parser import DocumentParser
from pdftranslator.domain.protocols.repositories import (
    ReadRepository,
    WriteRepository,
    GlossaryProgressTracker,
)


def test_embedding_provider_protocol():
    class MockEmbedder:
        def embed_query(self, text: str) -> list[float]:
            return [0.1, 0.2]
        def embed_documents(self, texts: list[str]) -> list[list[float]]:
            return [[0.1, 0.2]]
    assert isinstance(MockEmbedder(), EmbeddingProvider)


def test_reranking_provider_protocol():
    class MockReranker:
        def rerank(self, query: str, documents: list, top_n: int = 5) -> list:
            return documents[:top_n]
    assert isinstance(MockReranker(), RerankingProvider)


def test_audio_synthesizer_protocol():
    from pathlib import Path
    class MockSynth:
        @property
        def is_available(self) -> bool:
            return True
        @property
        def name(self) -> str:
            return "mock"
        def synthesize(self, text: str, output_path: Path, voice: str = "default", speed: float = 1.0, language: str = "es") -> bool:
            return True
        def merge_audio(self, audio_files: list[Path], output_path: Path) -> bool:
            return True
    assert isinstance(MockSynth(), AudioSynthesizer)


def test_document_parser_protocol():
    class MockParser:
        @property
        def supported_extensions(self) -> set[str]:
            return {".pdf", ".epub"}
        def parse(self, file_path: str) -> str | None:
            return "extracted text"
    assert isinstance(MockParser(), DocumentParser)


def test_glossary_progress_tracker_protocol():
    class MockTracker:
        def save_extracted(self, work_id: int, volume_id: int, entities: list) -> list:
            return []
        def get_pending_for_phase(self, work_id: int, volume_id: int, phase: str) -> list:
            return []
        def batch_update_phase(self, ids: list[int], phase: str, batch_num: int | None = None) -> None:
            pass
        def get_resume_point(self, work_id: int, volume_id: int) -> tuple[str, int | None]:
            return ("extracted", None)
        def cleanup_completed(self, volume_id: int) -> None:
            pass
    assert isinstance(MockTracker(), GlossaryProgressTracker)
