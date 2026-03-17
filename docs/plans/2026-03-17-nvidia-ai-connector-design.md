# Design: NvidiaAI Connector Implementation

**Date:** 2026-03-17
**Status:** Approved
**Goal:** Implement NvidiaAI class using langchain-nvidia-ai-endpoints to connect to NVIDIA NIM cloud API

## 1. Summary

Create `LLM/NvidiaAI.py` class that implements `LLMService` interface, following the same pattern as `OllamaAI`. The connector uses `ChatNVIDIA` from `langchain_nvidia_ai_endpoints` to access NVIDIA's hosted NIM models.

## 2. Current Architecture

```
LLMService (Abstract Base Class)
    ├── call_model(prompt: str) -> str
    ├── get_current_model_name() -> str
    ├── count_tokens(text: str) -> int
    └── split_into_limit(text: str) -> List[str]
```

Existing implementations:
- `GeminiAI` - connects to Google Gemini API
- `OllamaAI` - connects to local Ollama instance

## 3. Proposed Architecture

```
LLMService (Abstract Base Class)
    ↑
    └── NvidiaAI (NEW)
            ├── ChatNVIDIA (langchain_nvidia_ai_endpoints)
            ├── AutoTokenizer (HuggingFace - cached)
            └── NLTKTextSplitter (langchain_text_splitters)
```

**Flow:**
1. Initialization: Download/cache tokenizer → Initialize ChatNVIDIA
2. Call model: `invoke()` → log usage → return content
3. Count tokens: Use HuggingFace tokenizer
4. Split text: Use NLTKTextSplitter with token-based counting

## 4. Files to Create/Modify

### 4.1 CREATE: `LLM/NvidiaAI.py`

**Dependencies:**
```python
import logging
from pathlib import Path
from typing import List
from langchain_nvidia_ai_endpoints import ChatNVIDIA
from langchain_text_splitters import NLTKTextSplitter
from transformers import AutoTokenizer

from GlobalConfig import GlobalConfig
from LLM.llm_service import LLMService
```

**Class structure:**
```python
class NvidiaAI(LLMService):
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

    def call_model(self, prompt: str) -> str:
        response = self._model.invoke(prompt)
        self._logger.info(f"Call to '{self.get_current_model_name()}' successful. Usage: {response.usage_metadata}")
        return response.content

    def get_current_model_name(self) -> str:
        return self.config.nvidia_model_name

    def count_tokens(self, text: str) -> int:
        token_ids = self._tokenizer.encode(text, add_special_tokens=False)
        return len(token_ids)

    def split_into_limit(self, text: str) -> List[str]:
        text_splitter = NLTKTextSplitter(
            chunk_size=self.config.nvidia_context_size,
            chunk_overlap=0,
            language="english",
            length_function=self.count_tokens
        )
        return text_splitter.split_text(text)

    def _download_and_cache_tokenizer(self):
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

### 4.2 MODIFY: `requirements.txt`

Add:
```
langchain-nvidia-ai-endpoints
```

### 4.3 MODIFY: `environment.yml`

Add to dependencies under `pip:`:
```yaml
dependencies:
  - pip:
    - langchain-nvidia-ai-endpoints
```

**Note:** `GlobalConfig.py` already has all necessary NVIDIA configuration fields.

## 5. Environment Variables

**Required:**
```
NVIDIA_API_KEY=nvapi-*
```

**Example setup:**
```bash
export NVIDIA_API_KEY="nvapi-..."
```

## 6. Configuration Mapping

| GlobalConfig Field | ChatNVIDIA Parameter |
|-------------------|---------------------|
| `nvidia_model_name` | `model` |
| `nvidia_temperature` | `temperature` |
| `nvidia_top_p` | `top_p` |
| — | `verbose` = `True` |

**Current default:**
```python
nvidia_model_name = "meta/llama-3.3-70b-instruct"
nvidia_temperature = 0.2
nvidia_top_p = 0.95
nvidia_context_size = 3000
nvidia_local_tokenizer_dir = "llama-3.3-70b-instruct"
nvidia_local_tokenizer_name = "openai/gpt-oss-120b"
```

## 7. Error Handling

- **ImportError**: If `langchain_nvidia_ai_endpoints` not installed
- **API key errors**: Check `NVIDIA_API_KEY` is set and starts with `nvapi-`
- **Network errors**: Handle connection failures gracefully
- **Tokenizer download failures**: Log warning, fail gracefully

## 8. Success Criteria

- `NvidiaAI` implements all 4 methods from `LLMService`
- Can successfully call NVIDIA NIM cloud API
- Token counting works correctly
- Text splitting respects context window
- Configuration is loaded from `GlobalConfig`
- Dependency is added to `requirements.txt` and `environment.yml`
