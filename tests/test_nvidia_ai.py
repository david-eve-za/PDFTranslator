import os
import pytest
from llm.nvidia_llm import NvidiaLLM


@pytest.mark.skipif(
    os.environ.get("NVIDIA_API_KEY", "").startswith("nvapi-") is False,
    reason="NVIDIA_API_KEY not set",
)
def test_nvidia_ai_call_model():
    """Test calling NVIDIA NIM model."""
    nvidia = NvidiaLLM()
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
    nvidia = NvidiaLLM()
    count = nvidia.count_tokens("hello world")
    assert isinstance(count, int)
    assert count > 0


@pytest.mark.skipif(
    os.environ.get("NVIDIA_API_KEY", "").startswith("nvapi-") is False,
    reason="NVIDIA_API_KEY not set",
)
def test_nvidia_ai_split_into_limit():
    """Test text splitting."""
    nvidia = NvidiaLLM()
    text = "hello " * 10000  # Large text
    chunks = nvidia.split_into_limit(text)
    assert isinstance(chunks, list)
    assert len(chunks) > 0
    for chunk in chunks:
        tokens = nvidia.count_tokens(chunk)
        # Chunks are based on max_output_tokens * 3, not context_size
        assert tokens <= nvidia.config.nvidia_max_output_tokens * 3


@pytest.mark.skipif(
    os.environ.get("NVIDIA_API_KEY", "").startswith("nvapi-") is False,
    reason="NVIDIA_API_KEY not set",
)
def test_nvidia_ai_get_model_name():
    """Test getting current model name."""
    nvidia = NvidiaLLM()
    name = nvidia.get_current_model_name()
    assert isinstance(name, str)
    assert name.startswith("meta/")
