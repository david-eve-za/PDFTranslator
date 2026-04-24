import os
import pytest
from unittest.mock import MagicMock, patch
from llm.nvidia_llm import NvidiaLLM
from config.settings import Settings
from config.llm import LLMProvider, BCP47Language, NvidiaConfig, LLMSettings


def _create_mock_settings():
    """Create mock settings for testing."""
    settings = MagicMock(spec=Settings)
    settings.source_language = BCP47Language.ENGLISH
    settings.target_language = BCP47Language.SPANISH

    # Create NVIDIA config
    nvidia_config = MagicMock(spec=NvidiaConfig)
    nvidia_config.model_name = "meta/llama-3.1-8b-instruct"
    nvidia_config.temperature = 0.3
    nvidia_config.top_p = 0.9
    nvidia_config.max_output_tokens = 1024
    nvidia_config.rate_limit = 40
    nvidia_config.local_tokenizer_name = "meta-llama/Llama-3.1-8B"
    nvidia_config.local_tokenizer_dir = ".tokenizers/nvidia"

    # Create LLM settings
    llm_settings = MagicMock(spec=LLMSettings)
    llm_settings.agent = LLMProvider.NVIDIA
    llm_settings.nvidia = nvidia_config

    settings.llm = llm_settings
    return settings


@pytest.mark.skipif(
    os.environ.get("NVIDIA_API_KEY", "").startswith("nvapi-") is False,
    reason="NVIDIA_API_KEY not set",
)
def test_nvidia_ai_call_model():
    """Test calling NVIDIA NIM model."""
    settings = _create_mock_settings()
    nvidia = NvidiaLLM(settings)
    response = nvidia.call_model("Say 'test' and nothing else.")
    assert isinstance(response, str)
    assert len(response) > 0
    assert "test" in response.lower()


@pytest.mark.skipif(
    os.environ.get("NVIDIA_API_KEY", "").startswith("nvapi-") is False,
    reason="NVIDIA_API_KEY not set",
)
def test_nvidia_ai_count_tokens():
    """Test token counting."""
    settings = _create_mock_settings()
    nvidia = NvidiaLLM(settings)
    count = nvidia.count_tokens("hello world")
    assert isinstance(count, int)
    assert count > 0


@pytest.mark.skipif(
    os.environ.get("NVIDIA_API_KEY", "").startswith("nvapi-") is False,
    reason="NVIDIA_API_KEY not set",
)
def test_nvidia_ai_split_into_limit():
    """Test text splitting."""
    settings = _create_mock_settings()
    nvidia = NvidiaLLM(settings)
    text = "hello " * 10000  # Large text
    chunks = nvidia.split_into_limit(text)
    assert isinstance(chunks, list)
    assert len(chunks) > 0
    for chunk in chunks:
        tokens = nvidia.count_tokens(chunk)
        # Chunks are based on max_output_tokens * 3
        assert tokens <= settings.llm.nvidia.max_output_tokens * 3


@pytest.mark.skipif(
    os.environ.get("NVIDIA_API_KEY", "").startswith("nvapi-") is False,
    reason="NVIDIA_API_KEY not set",
)
def test_nvidia_ai_get_model_name():
    """Test getting current model name."""
    settings = _create_mock_settings()
    nvidia = NvidiaLLM(settings)
    name = nvidia.get_current_model_name()
    assert isinstance(name, str)
    assert name.startswith("meta/")
