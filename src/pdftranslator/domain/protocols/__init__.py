"""Domain protocols — interfaces that infrastructure must implement."""
from pdftranslator.domain.protocols.audio_synthesizer import (
    AudioSynthesizer,  # noqa: F401
)
from pdftranslator.domain.protocols.document_parser import DocumentParser  # noqa: F401
from pdftranslator.domain.protocols.embedding import EmbeddingProvider  # noqa: F401
from pdftranslator.domain.protocols.llm import (  # noqa: F401
    LLMClient,
    TextGenerator,
    TextSplitter,
    TokenCounter,
)
from pdftranslator.domain.protocols.repositories import (  # noqa: F401
    GlossaryProgressTracker,
    ReadRepository,
    WriteRepository,
)
from pdftranslator.domain.protocols.reranking import RerankingProvider  # noqa: F401

__all__ = [
    "TextGenerator", "TokenCounter", "TextSplitter", "LLMClient",
    "EmbeddingProvider", "RerankingProvider",
    "AudioSynthesizer", "DocumentParser",
    "ReadRepository", "WriteRepository", "GlossaryProgressTracker",
]
