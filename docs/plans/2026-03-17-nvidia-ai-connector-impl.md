# NvidiaAI Connector Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implement NvidiaAI class using langchain-nvidia-ai-endpoints to connect to NVIDIA NIM cloud API

**Architecture:** Create LLM/NvidiaAI.py implementing LLMService interface, using ChatNVIDIA for API calls, AutoTokenizer for token counting, and NLTKTextSplitter for text chunking.

**Tech Stack:** Python, langchain-nvidia-ai-endpoints, HuggingFace Transformers, langchain-text-splitters

---

## Task 1: Add dependency to requirements.txt

**Files:**
- Modify: `requirements.txt`

**Step 1: Open requirements.txt**

**Step 2: Add langchain-nvidia-ai-endpoints**

Add this line at the end:
```
langchain-nvidia-ai-endpoints
```

**Step 3: Verify file content**

Run: `tail -5 requirements.txt`

Expected: Last line shows `langchain-nvidia-ai-endpoints`

**Step 4: Commit**

```bash
git add requirements.txt
git commit -m "deps: add langchain-nvidia-ai-endpoints"
```

---

## Task 2: Add dependency to environment.yml

**Files:**
- Modify: `environment.yml`

**Step 1: Open environment.yml**

**Step 2: Add to pip dependencies**

Find the dependencies section and add to pip:
```yaml
- pip:
  - langchain-nvidia-ai-endpoints
```

**Step 3: Verify YAML syntax**

Run: `yamllint environment.yml` (if available) or `python -c "import yaml; yaml.safe_load(open('environment.yml'))"`

Expected: No syntax errors

**Step 4: Commit**

```bash
git add environment.yml
git commit -m "deps: add langchain-nvidia-ai-endpoints to environment.yml"
```

---

## Task 3: Create LLM/NvidiaAI.py - Skeleton with imports

**Files:**
- Create: `LLM/NvidiaAI.py`

**Step 1: Write the skeleton with imports**

```python
import logging
from pathlib import Path
from typing import List

from GlobalConfig import GlobalConfig
from LLM.llm_service import LLMService


class NvidiaAI(LLMService):
    """NVIDIA NIM cloud API connector using langchain-nvidia-ai-endpoints."""

    def __init__(self):
        self._logger = logging.getLogger(__name__)
        self.config = GlobalConfig()

    def call_model(self, prompt: str) -> str:
        pass

    def get_current_model_name(self) -> str:
        pass

    def count_tokens(self, text: str) -> int:
        pass

    def split_into_limit(self, text: str) -> List[str]:
        pass
```

**Step 2: Verify file compiles**

Run: `python -c "from LLM.NvidiaAI import NvidiaAI; print('OK')"`

Expected: `OK`

**Step 3: Commit**

```bash
git add LLM/NvidiaAI.py
git commit -m "feat: add NvidiaAI skeleton"
```

---

## Task 4: Implement __init__ method

**Files:**
- Modify: `LLM/NvidiaAI.py`

**Step 1: Add imports for ChatNVIDIA and AutoTokenizer**

Add at top after existing imports:
```python
from langchain_nvidia_ai_endpoints import ChatNVIDIA
from transformers import AutoTokenizer
```

**Step 2: Implement __init__ with tokenizer caching**

Replace the `__init__` method:
```python
def __init__(self):
    self._logger = logging.getLogger(__name__)
    self.config = GlobalConfig()
    self._tokenizer = self._download_and_cache_tokenizer()
    self._model = ChatNVIDIA(
        model=self.config.nvidia_model_name,
        temperature=self.config.nvidia_temperature,
        top_p=self.config.nvidia_top_p,
        verbose=True
    )
    self._logger.info(f"NvidiaAI initialized with model: {self.config.nvidia_model_name}")
```

**Step 3: Add _download_and_cache_tokenizer helper method**

Add at end of class:
```python
def _download_and_cache_tokenizer(self):
    """
    Downloads and caches the tokenizer if it doesn't already exist locally.
    """
    tokenizer_dir = Path(self.config.nvidia_local_tokenizer_dir)
    if tokenizer_dir.exists():
        self._logger.info(f"Tokenizer already cached in {tokenizer_dir}")
    else:
        self._logger.info(f"Downloading tokenizer for {self.config.nvidia_local_tokenizer_name}...")
        tokenizer = AutoTokenizer.from_pretrained(self.config.nvidia_local_tokenizer_name, use_fast=True)
        tokenizer_dir.mkdir(parents=True, exist_ok=True)
        tokenizer.save_pretrained(tokenizer_dir)
        self._logger.info(f"Tokenizer saved in {tokenizer_dir}")

    return AutoTokenizer.from_pretrained(tokenizer_dir, use_fast=True)
```

**Step 4: Verify file compiles**

Run: `python -c "from LLM.NvidiaAI import NvidiaAI; print('Imports OK')"`

Expected: `Imports OK`

**Step 5: Commit**

```bash
git add LLM/NvidiaAI.py
git commit -m "feat: implement NvidiaAI.__init__ with tokenizer caching"
```

---

## Task 5: Implement call_model method

**Files:**
- Modify: `LLM/NvidiaAI.py`

**Step 1: Add NLTKTextSplitter import**

Add at top:
```python
from langchain_text_splitters import NLTKTextSplitter
```

**Step 2: Implement call_model**

Replace the `call_model` method:
```python
def call_model(self, prompt: str) -> str:
    response = self._model.invoke(prompt)
    self._logger.info(f"Call to '{self.get_current_model_name()}' successful. Usage: {response.usage_metadata}")
    return response.content
```

**Step 3: Verify file compiles**

Run: `python -c "from LLM.NvidiaAI import NvidiaAI; NvidiaAI().call_model = NvidiaAI().call_model; print('OK')"`

Expected: `OK`

**Step 4: Commit**

```bash
git add LLM/NvidiaAI.py
git commit -m "feat: implement NvidiaAI.call_model"
```

---

## Task 6: Implement get_current_model_name method

**Files:**
- Modify: `LLM/NvidiaAI.py`

**Step 1: Implement get_current_model_name**

Replace the `get_current_model_name` method:
```python
def get_current_model_name(self) -> str:
    return self.config.nvidia_model_name
```

**Step 2: Verify file compiles**

Run: `python -c "from LLM.NvidiaAI import NvidiaAI; print(NvidiaAI().get_current_model_name())"`

Expected: `meta/llama-3.3-70b-instruct`

**Step 3: Commit**

```bash
git add LLM/NvidiaAI.py
git commit -m "feat: implement NvidiaAI.get_current_model_name"
```

---

## Task 7: Implement count_tokens method

**Files:**
- Modify: `LLM/NvidiaAI.py`

**Step 1: Implement count_tokens**

Replace the `count_tokens` method:
```python
def count_tokens(self, text: str) -> int:
    token_ids = self._tokenizer.encode(text, add_special_tokens=False)
    return len(token_ids)
```

**Step 2: Verify file compiles**

Run: `python -c "from LLM.NvidiaAI import NvidiaAI; n = NvidiaAI(); print(n.count_tokens('hello world'))"`

Expected: A number (token count) like `2` or `3`

**Step 3: Commit**

```bash
git add LLM/NvidiaAI.py
git commit -m "feat: implement NvidiaAI.count_tokens"
```

---

## Task 8: Implement split_into_limit method

**Files:**
- Modify: `LLM/NvidiaAI.py`

**Step 1: Implement split_into_limit**

Replace the `split_into_limit` method:
```python
def split_into_limit(self, text: str) -> List[str]:
    text_splitter = NLTKTextSplitter(
        chunk_size=self.config.nvidia_context_size,
        chunk_overlap=0,
        language="english",
        length_function=self.count_tokens
    )
    return text_splitter.split_text(text)
```

**Step 2: Verify file compiles**

Run: `python -c "from LLM.NvidiaAI import NvidiaAI; n = NvidiaAI(); print(len(n.split_into_limit('hello ' * 1000)))"`

Expected: A number >= 1

**Step 3: Commit**

```bash
git add LLM/NvidiaAI.py
git commit -m "feat: implement NvidiaAI.split_into_limit"
```

---

## Task 9: Create integration test

**Files:**
- Create: `tests/test_nvidia_ai.py`

**Step 1: Write the integration test**

```python
import os
import pytest
from LLM.NvidiaAI import NvidiaAI


@pytest.mark.skipif(
    os.environ.get("NVIDIA_API_KEY", "").startswith("nvapi-") is False,
    reason="NVIDIA_API_KEY not set"
)
def test_nvidia_ai_call_model():
    """Test calling NVIDIA NIM model."""
    nvidia = NvidiaAI()
    response = nvidia.call_model("Say 'test' and nothing else.")
    assert isinstance(response, str)
    assert len(response) > 0
    assert "test" in response.lower()


@pytest.mark.skipif(
    os.environ.get("NVIDIA_API_KEY", "").startswith("nvapi-") is False,
    reason="NVIDIA_API_KEY not set"
)
def test_nvidia_ai_count_tokens():
    """Test token counting."""
    nvidia = NvidiaAI()
    count = nvidia.count_tokens("hello world")
    assert isinstance(count, int)
    assert count > 0


@pytest.mark.skipif(
    os.environ.get("NVIDIA_API_KEY", "").startswith("nvapi-") is False,
    reason="NVIDIA_API_KEY not set"
)
def test_nvidia_ai_split_into_limit():
    """Test text splitting."""
    nvidia = NvidiaAI()
    text = "hello " * 10000  # Large text
    chunks = nvidia.split_into_limit(text)
    assert isinstance(chunks, list)
    assert len(chunks) > 0
    for chunk in chunks:
        tokens = nvidia.count_tokens(chunk)
        assert tokens <= nvidia.config.nvidia_context_size


@pytest.mark.skipif(
    os.environ.get("NVIDIA_API_KEY", "").startswith("nvapi-") is False,
    reason="NVIDIA_API_KEY not set"
)
def test_nvidia_ai_get_model_name():
    """Test getting current model name."""
    nvidia = NvidiaAI()
    name = nvidia.get_current_model_name()
    assert isinstance(name, str)
    assert name.startswith("meta/")
```

**Step 2: Verify test file compiles**

Run: `python -c "import tests.test_nvidia_ai; print('OK')"`

Expected: `OK`

**Step 3: Run tests (will skip without API key)**

Run: `pytest tests/test_nvidia_ai.py -v`

Expected: Tests skip due to missing API key, or pass if API key is set

**Step 4: Commit**

```bash
git add tests/test_nvidia_ai.py
git commit -m "test: add NvidiaAI integration tests"
```

---

## Task 10: Verify complete implementation

**Step 1: Run all tests**

Run: `pytest tests/ -v`

Expected: All tests pass (NVIDIA tests will skip without API key)

**Step 2: Verify NvidiaAI implements LLMService**

Run: `python -c "from LLM.NvidiaAI import NvidiaAI; from LLM.llm_service import LLMService; assert issubclass(NvidiaAI, LLMService); print('OK')"`

Expected: `OK`

**Step 3: Check final implementation**

Review LLM/NvidiaAI.py:
- All 4 abstract methods implemented
- ChatNVIDIA initialized with config
- AutoTokenizer cached
- NLTKTextSplitter configured

**Step 4: Final commit if needed**

```bash
git add -A
git commit -m "Finish NvidiaAI connector implementation"
```

---

## Summary

After completion:
- `LLM/NvidiaAI.py` created with full implementation
- `requirements.txt` updated with langchain-nvidia-ai-endpoints
- `environment.yml` updated with dependency
- Integration tests in `tests/test_nvidia_ai.py`
- Compatible with existing LLMService interface
- Follows same pattern as OllamaAI

**Environment Variables Required:**
- `NVIDIA_API_KEY` (format `nvapi-*`)
