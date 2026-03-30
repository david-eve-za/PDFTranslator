# SOLID Refactoring Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Refactor PDFTranslator to follow SOLID principles with Pydantic Settings, Factory Pattern, and dependency injection.

**Architecture:** Configuration is split into domain-specific Pydantic models. LLM clients are created via Factory pattern. Services receive dependencies through constructor injection. CLI is separated into UI and business logic.

**Tech Stack:** Python 3.11+, Pydantic v2, pydantic-settings, Typer, Rich, LangChain

---

## Phase 1: Configuration System (Pydantic Settings)

### Task 1.1: Create config package structure

**Files:**
- Create: `config/__init__.py`
- Create: `config/llm.py`
- Create: `config/database.py`
- Create: `config/nlp.py`
- Create: `config/paths.py`
- Create: `config/settings.py`

**Step 1: Create config directory**
```bash
mkdir -p config
```

**Step 2: Create config/__init__.py**
```python
"""Configuration module using Pydantic Settings."""

from config.settings import Settings
from config.llm import LLMSettings, LLMProvider, BCP47Language

__all__ = ["Settings", "LLMSettings", "LLMProvider", "BCP47Language"]
```

**Step 3: Create config/llm.py**
```python
"""LLM configuration models."""

from enum import Enum
from pydantic import BaseModel, Field


class LLMProvider(str, Enum):
    """Supported LLM providers."""
    GEMINI = "gemini"
    NVIDIA = "nvidia"
    OLLAMA = "ollama"


class BCP47Language(str, Enum):
    """BCP 47 language codes for text splitting."""
    ENGLISH = "en"
    SPANISH = "es"
    CHINESE = "zh"
    JAPANESE = "ja"
    KOREAN = "ko"
    FRENCH = "fr"
    GERMAN = "de"
    ITALIAN = "it"
    PORTUGUESE = "pt"
    RUSSIAN = "ru"
    ARABIC = "ar"
    HINDI = "hi"


class GeminiConfig(BaseModel):
    """Google Gemini configuration."""
    model_names: list[str] = Field(
        default_factory=lambda: ["gemini-2.0-flash"],
        description="List of Gemini model names to use"
    )
    temperature: float = Field(default=0.3, ge=0.0, le=2.0)
    top_p: float = Field(default=0.95, ge=0.0, le=1.0)
    top_k: int = Field(default=40, ge=1)
    context_size: int = Field(default=1000000, gt=0)
    rate_limit: int = Field(default=15, gt=0, description="Requests per minute")
    max_bucket_size: int = Field(default=10, gt=0)
    request_timeout: int = Field(default=60, gt=0)
    retry_attempts: int = Field(default=3, gt=0)


class NvidiaConfig(BaseModel):
    """NVIDIA NIM configuration."""
    model_name: str = Field(default="meta/llama-3.1-8b-instruct")
    temperature: float = Field(default=0.3, ge=0.0, le=2.0)
    top_p: float = Field(default=0.95, ge=0.0, le=1.0)
    max_output_tokens: int = Field(default=4096, gt=0)
    rate_limit: int = Field(default=30, gt=0, description="Requests per minute")
    local_tokenizer_name: str = Field(default="meta-llama/Llama-3.1-8B")
    local_tokenizer_dir: str = Field(default=".tokenizers/nvidia")


class OllamaConfig(BaseModel):
    """Ollama local LLM configuration."""
    model_name: str = Field(default="llama3.2")
    temperature: float = Field(default=0.3, ge=0.0, le=2.0)
    top_p: float = Field(default=0.9, ge=0.0, le=1.0)
    context_size: int = Field(default=4096, gt=0)
    validate_model: bool = Field(default=True)
    local_tokenizer_name: str = Field(default="meta-llama/Llama-3.1-8B")
    local_tokenizer_dir: str = Field(default=".tokenizers/ollama")
    model_id: str = Field(default="meta-llama/Llama-3.1-8B-Instruct")


class LLMSettings(BaseModel):
    """LLM settings aggregating all provider configs."""
    agent: LLMProvider = Field(default=LLMProvider.NVIDIA)
    gemini: GeminiConfig = Field(default_factory=GeminiConfig)
    nvidia: NvidiaConfig = Field(default_factory=NvidiaConfig)
    ollama: OllamaConfig = Field(default_factory=OllamaConfig)

    def get_config_for_provider(self, provider: LLMProvider) -> BaseModel:
        """Get configuration for a specific provider."""
        configs = {
            LLMProvider.GEMINI: self.gemini,
            LLMProvider.NVIDIA: self.nvidia,
            LLMProvider.OLLAMA: self.ollama,
        }
        return configs[provider]
```

**Step 4: Create config/database.py**
```python
"""Database configuration models."""

from pydantic import BaseModel, Field


class DatabaseSettings(BaseModel):
    """Database connection settings."""
    host: str = Field(default="localhost")
    port: int = Field(default=5432, gt=0)
    name: str = Field(default="pdftranslator")
    user: str = Field(default="postgres")
    password: str = Field(default="postgres")
    min_connections: int = Field(default=1, ge=1)
    max_connections: int = Field(default=10, ge=1)

    @property
    def connection_string(self) -> str:
        """Build PostgreSQL connection string."""
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.name}"

    @property
    def async_connection_string(self) -> str:
        """Build async PostgreSQL connection string."""
        return f"postgresql+asyncpg://{self.user}:{self.password}@{self.host}:{self.port}/{self.name}"
```

**Step 5: Create config/nlp.py**
```python
"""NLP configuration models."""

from pydantic import BaseModel, Field


class NLPSettings(BaseModel):
    """NLP and entity extraction settings."""
    ner_model: str = Field(default="en_core_web_sm")
    entity_types: list[str] = Field(
        default_factory=lambda: ["PERSON", "ORG", "GPE", "LOC", "NORP", "FAC", "PRODUCT", "EVENT", "WORK_OF_ART", "LAW"],
        description="spaCy entity types to extract"
    )
    min_entity_length: int = Field(default=2, ge=1)
    max_entity_length: int = Field(default=100, ge=1)
    confidence_threshold: float = Field(default=0.5, ge=0.0, le=1.0)
```

**Step 6: Create config/paths.py**
```python
"""Path configuration models."""

from pathlib import Path
from pydantic import BaseModel, Field


class PathSettings(BaseModel):
    """Application path settings."""
    base_dir: Path = Field(default_factory=lambda: Path.cwd())
    audiobooks_dir: Path = Field(default_factory=lambda: Path("audiobooks"))
    videos_dir: Path = Field(default_factory=lambda: Path("videos"))
    translation_prompt_path: Path = Field(
        default_factory=lambda: Path("tools/translation_prompt.txt")
    )
    tokenizer_path: Path = Field(
        default_factory=lambda: Path.home() / ".cache" / "sentencepiece" / "tokenizer.model"
    )

    def ensure_directories(self) -> None:
        """Create output directories if they don't exist."""
        self.audiobooks_dir.mkdir(parents=True, exist_ok=True)
        self.videos_dir.mkdir(parents=True, exist_ok=True)
```

**Step 7: Create config/settings.py**
```python
"""Main application settings using Pydantic Settings."""

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

from config.llm import LLMSettings, LLMProvider
from config.database import DatabaseSettings
from config.nlp import NLPSettings
from config.paths import PathSettings


class Settings(BaseSettings):
    """
    Main application settings with nested configuration.
    
    Configuration is loaded from (in order of priority):
    1. Environment variables (highest priority)
    2. .env file
    3. Default values (lowest priority)
    
    Environment variables use double underscore separator for nested values:
    LLM__AGENT=nvidia
    LLM__NVIDIA__TEMPERATURE=0.5
    """
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        extra="ignore",
        case_sensitive=False,
    )
    
    # Nested configurations
    llm: LLMSettings = Field(default_factory=LLMSettings)
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    nlp: NLPSettings = Field(default_factory=NLPSettings)
    paths: PathSettings = Field(default_factory=PathSettings)
    
    # Singleton instance for backward compatibility
    _instance: "Settings | None" = None
    
    @classmethod
    def get(cls) -> "Settings":
        """
        Get the singleton settings instance.
        
        Creates a new instance if one doesn't exist.
        Use Settings.reset() to clear the singleton for testing.
        """
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    @classmethod
    def reset(cls) -> None:
        """Reset the singleton instance. Useful for testing."""
        cls._instance = None
    
    @property
    def agent(self) -> LLMProvider:
        """Convenience property for LLM agent selection."""
        return self.llm.agent
```

**Step 8: Add pydantic-settings to dependencies**
```bash
# Add to environment.yml or requirements.txt
pip install pydantic-settings
```

**Step 9: Commit Phase 1.1**
```bash
git add config/
git commit -m "feat(config): add Pydantic Settings configuration system

- Add config package with domain-specific settings
- LLMSettings with Gemini, NVIDIA, Ollama configs
- DatabaseSettings for connection configuration
- NLPSettings for entity extraction
- PathSettings for application paths
- Settings singleton with environment variable support"
```

---

### Task 1.2: Create backward compatibility wrapper

**Files:**
- Create: `GlobalConfig.py` (wrapper)

**Step 1: Create GlobalConfig.py wrapper**
```python
"""
Backward compatibility wrapper for GlobalConfig.

DEPRECATED: Use config.settings.Settings instead.
This module will be removed in a future version.
"""

import warnings
from config.settings import Settings
from config.llm import LLMProvider, BCP47Language

# Suppress deprecation warning for now during transition
# warnings.warn(
#     "GlobalConfig is deprecated. Use config.settings.Settings instead.",
#     DeprecationWarning,
#     stacklevel=2
# )

# Create singleton instance for backward compatibility
_settings = Settings.get()


class GlobalConfig:
    """
    Backward compatibility wrapper for Settings.
    
    This class provides the same interface as the old GlobalConfig
    but delegates to the new Pydantic Settings system.
    """
    
    def __init__(self):
        self._settings = Settings.get()
    
    # LLM Provider properties
    @property
    def agent(self) -> str:
        return self._settings.llm.agent.value
    
    # Gemini properties
    @property
    def gemini_model_names(self) -> list[str]:
        return self._settings.llm.gemini.model_names
    
    @property
    def gemini_temperature(self) -> float:
        return self._settings.llm.gemini.temperature
    
    @property
    def gemini_top_p(self) -> float:
        return self._settings.llm.gemini.top_p
    
    @property
    def gemini_top_k(self) -> int:
        return self._settings.llm.gemini.top_k
    
    @property
    def gemini_context_size(self) -> int:
        return self._settings.llm.gemini.context_size
    
    @property
    def gemini_model_rate_limit(self) -> int:
        return self._settings.llm.gemini.rate_limit
    
    @property
    def gemini_max_bucket_size(self) -> int:
        return self._settings.llm.gemini.max_bucket_size
    
    @property
    def gemini_request_timeout(self) -> int:
        return self._settings.llm.gemini.request_timeout
    
    @property
    def gemini_retry_attempts(self) -> int:
        return self._settings.llm.gemini.retry_attempts
    
    @property
    def gemini_default_fallback_rpm(self) -> int:
        return self._settings.llm.gemini.rate_limit
    
    @property
    def gemini_model_rate_limits(self) -> dict[str, int]:
        # Return dict with model names as keys
        return {name: self._settings.llm.gemini.rate_limit for name in self._settings.llm.gemini.model_names}
    
    @property
    def gemini_temperature_prop(self) -> float:
        return self._settings.llm.gemini.temperature
    
    # NVIDIA properties
    @property
    def nvidia_model_name(self) -> str:
        return self._settings.llm.nvidia.model_name
    
    @property
    def nvidia_temperature(self) -> float:
        return self._settings.llm.nvidia.temperature
    
    @property
    def nvidia_top_p(self) -> float:
        return self._settings.llm.nvidia.top_p
    
    @property
    def nvidia_max_output_tokens(self) -> int:
        return self._settings.llm.nvidia.max_output_tokens
    
    @property
    def nvidia_model_rate_limit(self) -> int:
        return self._settings.llm.nvidia.rate_limit
    
    @property
    def nvidia_local_tokenizer_name(self) -> str:
        return self._settings.llm.nvidia.local_tokenizer_name
    
    @property
    def nvidia_local_tokenizer_dir(self) -> str:
        return self._settings.llm.nvidia.local_tokenizer_dir
    
    # Ollama properties
    @property
    def ollama_default_model_name(self) -> str:
        return self._settings.llm.ollama.model_name
    
    @property
    def ollama_temperature(self) -> float:
        return self._settings.llm.ollama.temperature
    
    @property
    def ollama_top_p(self) -> float:
        return self._settings.llm.ollama.top_p
    
    @property
    def ollama_context_size(self) -> int:
        return self._settings.llm.ollama.context_size
    
    @property
    def ollama_validate_model(self) -> bool:
        return self._settings.llm.ollama.validate_model
    
    @property
    def ollama_local_tokenizer_name(self) -> str:
        return self._settings.llm.ollama.local_tokenizer_name
    
    @property
    def ollama_local_tokenizer_dir(self) -> str:
        return self._settings.llm.ollama.local_tokenizer_dir
    
    @property
    def ollama_model_id(self) -> str:
        return self._settings.llm.ollama.model_id
    
    # Database properties
    @property
    def db_host(self) -> str:
        return self._settings.database.host
    
    @property
    def db_port(self) -> int:
        return self._settings.database.port
    
    @property
    def db_name(self) -> str:
        return self._settings.database.name
    
    @property
    def db_user(self) -> str:
        return self._settings.database.user
    
    @property
    def db_password(self) -> str:
        return self._settings.database.password
    
    @property
    def db_min_connections(self) -> int:
        return self._settings.database.min_connections
    
    @property
    def db_max_connections(self) -> int:
        return self._settings.database.max_connections
    
    # NLP properties
    @property
    def ner_model(self) -> str:
        return self._settings.nlp.ner_model
    
    @property
    def ner_entity_types(self) -> list[str]:
        return self._settings.nlp.entity_types
    
    # Path properties
    @property
    def translation_prompt_path(self) -> str:
        return str(self._settings.paths.translation_prompt_path)
    
    @property
    def tokenizer_path(self) -> str:
        return str(self._settings.paths.tokenizer_path)


# Export BCP47Language for backward compatibility
__all__ = ["GlobalConfig", "BCP47Language"]
```

**Step 2: Test backward compatibility**
```bash
python -c "from GlobalConfig import GlobalConfig; g = GlobalConfig(); print(g.agent, g.nvidia_model_name)"
```

**Step 3: Commit**
```bash
git add GlobalConfig.py
git commit -m "feat(config): add backward compatibility wrapper for GlobalConfig

- Wraps new Settings system with old GlobalConfig interface
- Maintains compatibility with existing code during migration
- All 30+ properties preserved"
```

---

## Phase 2: LLM Infrastructure

### Task 2.1: Create infrastructure/llm package

**Files:**
- Create: `infrastructure/__init__.py`
- Create: `infrastructure/llm/__init__.py`
- Create: `infrastructure/llm/protocol.py`
- Create: `infrastructure/llm/base.py`
- Create: `infrastructure/llm/factory.py`

**Step 1: Create infrastructure directory**
```bash
mkdir -p infrastructure/llm
```

**Step 2: Create infrastructure/__init__.py**
```python
"""Infrastructure layer for external integrations."""
```

**Step 3: Create infrastructure/llm/__init__.py**
```python
"""LLM infrastructure module."""

from infrastructure.llm.protocol import LLMClient
from infrastructure.llm.base import BaseLLM
from infrastructure.llm.factory import LLMFactory

__all__ = ["LLMClient", "BaseLLM", "LLMFactory"]
```

**Step 4: Create infrastructure/llm/protocol.py**
```python
"""LLM Client Protocol definition."""

from typing import Protocol, runtime_checkable

from config.llm import BCP47Language


@runtime_checkable
class LLMClient(Protocol):
    """
    Protocol defining the LLM client interface.
    
    Any class implementing these methods can be used as an LLM client,
    enabling duck typing and easy mocking for tests.
    """
    
    def call_model(self, prompt: str) -> str:
        """
        Call the LLM model with a prompt.
        
        Args:
            prompt: The prompt to send to the model.
            
        Returns:
            The model's response as a string.
            
        Raises:
            LLMError: If the call fails.
        """
        ...
    
    def get_current_model_name(self) -> str:
        """
        Get the name of the currently active model.
        
        Returns:
            Model name string.
        """
        ...
    
    def count_tokens(self, text: str) -> int:
        """
        Count the number of tokens in a text.
        
        Args:
            text: The text to count tokens for.
            
        Returns:
            Number of tokens.
        """
        ...
    
    def split_into_limit(
        self, text: str, language: BCP47Language = BCP47Language.ENGLISH
    ) -> list[str]:
        """
        Split text into chunks that fit within token limits.
        
        Args:
            text: The text to split.
            language: Language for tokenization (default: English).
            
        Returns:
            List of text chunks.
        """
        ...
```

**Step 5: Create infrastructure/llm/base.py**
```python
"""Base LLM implementation with common functionality."""

from abc import ABC, abstractmethod
from typing import List

from config.settings import Settings
from config.llm import BCP47Language


class BaseLLM(ABC):
    """
    Abstract base class for LLM implementations.
    
    Provides common initialization and enforces the LLM interface.
    Subclasses must implement all abstract methods.
    """
    
    def __init__(self, settings: Settings):
        """
        Initialize the LLM with settings.
        
        Args:
            settings: Application settings containing LLM configuration.
        """
        self._settings = settings
    
    @abstractmethod
    def call_model(self, prompt: str) -> str:
        """Call the LLM model with a prompt."""
        pass
    
    @abstractmethod
    def get_current_model_name(self) -> str:
        """Get the name of the currently active model."""
        pass
    
    @abstractmethod
    def count_tokens(self, text: str) -> int:
        """Count the number of tokens in a text."""
        pass
    
    @abstractmethod
    def split_into_limit(
        self, text: str, language: BCP47Language = BCP47Language.ENGLISH
    ) -> List[str]:
        """Split text into chunks that fit within token limits."""
        pass
```

**Step 6: Create infrastructure/llm/factory.py**
```python
"""Factory for creating LLM clients."""

import logging
from typing import Type

from config.settings import Settings
from config.llm import LLMProvider
from infrastructure.llm.protocol import LLMClient
from infrastructure.llm.base import BaseLLM

logger = logging.getLogger(__name__)


class LLMFactory:
    """
    Factory for creating LLM clients based on configuration.
    
    Implements the Factory Pattern to decouple client creation
    from the calling code. Supports singleton instances per provider.
    
    Usage:
        factory = LLMFactory(settings)
        client = factory.create()  # Uses default provider from settings
        client = factory.create(LLMProvider.GEMINI)  # Specific provider
    """
    
    def __init__(self, settings: Settings):
        """
        Initialize the factory with settings.
        
        Args:
            settings: Application settings containing LLM configuration.
        """
        self._settings = settings
        self._instances: dict[LLMProvider, LLMClient] = {}
    
    def create(self, provider: LLMProvider | None = None) -> LLMClient:
        """
        Create or retrieve an LLM client instance.
        
        Uses singleton pattern per provider - creates once, reuses after.
        
        Args:
            provider: Specific provider to use. If None, uses the
                     provider configured in settings.llm.agent.
        
        Returns:
            LLM client instance.
            
        Raises:
            ValueError: If the provider is not supported.
        """
        provider = provider or self._settings.llm.agent
        
        # Return existing instance if available (singleton per provider)
        if provider in self._instances:
            logger.debug(f"Reusing existing {provider.value} client instance")
            return self._instances[provider]
        
        # Create new instance
        logger.info(f"Creating new {provider.value} client instance")
        client = self._create_client(provider)
        self._instances[provider] = client
        return client
    
    def _create_client(self, provider: LLMProvider) -> LLMClient:
        """
        Create a new LLM client for the given provider.
        
        Args:
            provider: Provider to create client for.
            
        Returns:
            New LLM client instance.
            
        Raises:
            ValueError: If provider is not supported.
        """
        # Import here to avoid circular imports and allow lazy loading
        if provider == LLMProvider.GEMINI:
            from infrastructure.llm.gemini import GeminiLLM
            return GeminiLLM(self._settings)
        
        elif provider == LLMProvider.NVIDIA:
            from infrastructure.llm.nvidia import NvidiaLLM
            return NvidiaLLM(self._settings)
        
        elif provider == LLMProvider.OLLAMA:
            from infrastructure.llm.ollama import OllamaLLM
            return OllamaLLM(self._settings)
        
        raise ValueError(f"Unsupported LLM provider: {provider}")
    
    def clear_instances(self) -> None:
        """Clear all cached instances. Useful for testing."""
        self._instances.clear()
```

**Step 7: Commit**
```bash
git add infrastructure/
git commit -m "feat(infrastructure): add LLM factory and base classes

- Add LLMClient Protocol for duck typing
- Add BaseLLM abstract class with Settings injection
- Add LLMFactory with singleton per provider pattern
- Support for lazy loading of provider implementations"
```

---

### Task 2.2: Migrate NVIDIA LLM to new structure

**Files:**
- Create: `infrastructure/llm/nvidia.py`
- Modify: `llm/nvidia_llm.py` (update to use new base)

**Step 1: Create infrastructure/llm/nvidia.py**
```python
"""NVIDIA NIM LLM implementation."""

import logging
from pathlib import Path
from typing import List

from langchain_core.rate_limiters import InMemoryRateLimiter
from langchain_nvidia_ai_endpoints import ChatNVIDIA
from langchain_text_splitters import NLTKTextSplitter
from transformers import AutoTokenizer

from config.settings import Settings
from config.llm import BCP47Language, LLMProvider
from infrastructure.llm.base import BaseLLM

logger = logging.getLogger(__name__)


class NvidiaLLM(BaseLLM):
    """NVIDIA NIM cloud API connector using langchain-nvidia-ai-endpoints."""
    
    def __init__(self, settings: Settings):
        """
        Initialize NVIDIA LLM with settings.
        
        Args:
            settings: Application settings containing NVIDIA configuration.
        """
        super().__init__(settings)
        
        # Get NVIDIA-specific config
        config = settings.llm.nvidia
        
        # Initialize tokenizer
        self._tokenizer = self._load_tokenizer(config)
        
        # Create rate limiter
        rpm = config.rate_limit
        requests_per_second = rpm / 60.0
        logger.info(f"Creating NVIDIA LLM client with rate limit of {rpm} RPM")
        
        rate_limiter = InMemoryRateLimiter(
            requests_per_second=requests_per_second,
            max_bucket_size=rpm,
        )
        
        # Create model
        self._model = ChatNVIDIA(
            model=config.model_name,
            temperature=config.temperature,
            top_p=config.top_p,
            max_tokens=config.max_output_tokens,
            rate_limiter=rate_limiter,
            verbose=True,
        )
        
        logger.info(f"NvidiaLLM initialized with model: {config.model_name}")
    
    def call_model(self, prompt: str) -> str:
        """Call the NVIDIA model with a prompt."""
        response = self._model.invoke(prompt)
        logger.info(
            f"Call to '{self.get_current_model_name()}' successful. "
            f"Usage: {response.usage_metadata}"
        )
        return response.content
    
    def get_current_model_name(self) -> str:
        """Get the current model name."""
        return self._settings.llm.nvidia.model_name
    
    def count_tokens(self, text: str) -> int:
        """Count tokens using the tokenizer."""
        token_ids = self._tokenizer.encode(text, add_special_tokens=False)
        return len(token_ids)
    
    def split_into_limit(
        self, text: str, language: BCP47Language = BCP47Language.ENGLISH
    ) -> List[str]:
        """
        Split text into chunks for translation.
        
        Args:
            text: Text to split.
            language: BCP 47 language code for splitting.
            
        Returns:
            List of text chunks.
        """
        # Use 3x output tokens as chunk size (input can be larger)
        chunk_size = self._settings.llm.nvidia.max_output_tokens * 3
        
        text_splitter = NLTKTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=0,
            language=language.value,
            length_function=self.count_tokens,
        )
        
        return text_splitter.split_text(text)
    
    def _load_tokenizer(self, config):
        """Load or download tokenizer."""
        tokenizer_dir = Path(config.local_tokenizer_dir)
        
        if tokenizer_dir.exists():
            logger.info(f"Tokenizer already cached in {tokenizer_dir}")
        else:
            logger.info(f"Downloading tokenizer for {config.local_tokenizer_name}...")
            tokenizer = AutoTokenizer.from_pretrained(
                config.local_tokenizer_name, use_fast=True
            )
            tokenizer_dir.mkdir(parents=True, exist_ok=True)
            tokenizer.save_pretrained(tokenizer_dir)
            logger.info(f"Tokenizer saved in {tokenizer_dir}")
        
        return AutoTokenizer.from_pretrained(tokenizer_dir, use_fast=True)
```

**Step 2: Update llm/nvidia_llm.py to import from new location**
```python
# llm/nvidia_llm.py
"""
DEPRECATED: Use infrastructure.llm.nvidia instead.
This module is kept for backward compatibility.
"""

from infrastructure.llm.nvidia import NvidiaLLM

__all__ = ["NvidiaLLM"]
```

**Step 3: Commit**
```bash
git add infrastructure/llm/nvidia.py llm/nvidia_llm.py
git commit -m "feat(infrastructure): migrate NvidiaLLM to new structure

- Create NvidiaLLM in infrastructure/llm with Settings injection
- Add backward compatibility import in old location
- Support BCP47Language parameter in split_into_limit"
```

---

### Task 2.3: Migrate Ollama LLM

**Files:**
- Create: `infrastructure/llm/ollama.py`
- Modify: `llm/ollama_llm.py`

**Step 1: Create infrastructure/llm/ollama.py**
```python
"""Ollama local LLM implementation."""

import logging
from pathlib import Path
from typing import List

from langchain_ollama import ChatOllama
from langchain_text_splitters import NLTKTextSplitter
from transformers import AutoTokenizer

from config.settings import Settings
from config.llm import BCP47Language
from infrastructure.llm.base import BaseLLM

logger = logging.getLogger(__name__)


class OllamaLLM(BaseLLM):
    """Ollama local LLM connector using langchain-ollama."""
    
    def __init__(self, settings: Settings):
        """
        Initialize Ollama LLM with settings.
        
        Args:
            settings: Application settings containing Ollama configuration.
        """
        super().__init__(settings)
        
        config = settings.llm.ollama
        self._tokenizer = self._load_tokenizer(config)
        
        self._model = ChatOllama(
            model=config.model_name,
            validate_model_on_init=config.validate_model,
            temperature=config.temperature,
            top_p=config.top_p,
            verbose=True,
            reasoning=False,
        )
        
        logger.info(f"OllamaLLM initialized with model: {config.model_name}")
    
    def call_model(self, prompt: str) -> str:
        """Call the Ollama model with a prompt."""
        response = self._model.invoke(prompt)
        logger.info(
            f"Call to '{self.get_current_model_name()}' successful. "
            f"Usage: {response.usage_metadata}"
        )
        return response.content
    
    def get_current_model_name(self) -> str:
        """Get the current model name."""
        return self._settings.llm.ollama.model_name
    
    def count_tokens(self, text: str) -> int:
        """Count tokens using the tokenizer."""
        token_ids = self._tokenizer.encode(text, add_special_tokens=False)
        return len(token_ids)
    
    def split_into_limit(
        self, text: str, language: BCP47Language = BCP47Language.ENGLISH
    ) -> List[str]:
        """Split text into chunks for translation."""
        text_splitter = NLTKTextSplitter(
            chunk_size=self._settings.llm.ollama.context_size,
            chunk_overlap=0,
            language=language.value,
            length_function=self.count_tokens,
        )
        return text_splitter.split_text(text)
    
    def _load_tokenizer(self, config):
        """Load or download tokenizer."""
        tokenizer_dir = Path(config.local_tokenizer_dir)
        
        if tokenizer_dir.exists():
            logger.info(f"Tokenizer already cached in {tokenizer_dir}")
        else:
            logger.info(f"Downloading tokenizer for {config.model_id}...")
            tokenizer = AutoTokenizer.from_pretrained(
                config.local_tokenizer_name, use_fast=True
            )
            tokenizer_dir.mkdir(parents=True, exist_ok=True)
            tokenizer.save_pretrained(tokenizer_dir)
            logger.info(f"Tokenizer saved in {tokenizer_dir}")
        
        return AutoTokenizer.from_pretrained(tokenizer_dir, use_fast=True)
```

**Step 2: Update llm/ollama_llm.py**
```python
# llm/ollama_llm.py
"""
DEPRECATED: Use infrastructure.llm.ollama instead.
This module is kept for backward compatibility.
"""

from infrastructure.llm.ollama import OllamaLLM

__all__ = ["OllamaLLM"]
```

**Step 3: Commit**
```bash
git add infrastructure/llm/ollama.py llm/ollama_llm.py
git commit -m "feat(infrastructure): migrate OllamaLLM to new structure

- Create OllamaLLM in infrastructure/llm with Settings injection
- Add backward compatibility import in old location
- Support BCP47Language parameter in split_into_limit"
```

---

### Task 2.4: Migrate Gemini LLM

**Files:**
- Create: `infrastructure/llm/gemini.py`
- Modify: `llm/gemini_llm.py`

**Step 1: Create infrastructure/llm/gemini.py**
```python
"""Google Gemini LLM implementation."""

import logging
import os
import time
from pathlib import Path
from typing import List

import sentencepiece as spm
from google import genai
from google.api_core import exceptions as google_exceptions
from langchain_core.rate_limiters import InMemoryRateLimiter
from langchain_core.runnables import Runnable
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_text_splitters import NLTKTextSplitter

from config.settings import Settings
from config.llm import BCP47Language
from infrastructure.llm.base import BaseLLM

logger = logging.getLogger(__name__)


class GeminiLLM(BaseLLM):
    """Google Gemini LLM connector with model rotation support."""
    
    def __init__(self, settings: Settings):
        """
        Initialize Gemini LLM with settings.
        
        Args:
            settings: Application settings containing Gemini configuration.
        """
        super().__init__(settings)
        
        config = settings.llm.gemini
        self.genai_client = genai.Client()
        
        if not config.model_names:
            raise ValueError("Gemini model names list cannot be empty")
        
        self.model_names = config.model_names
        self._current_model_index = 0
        
        # Get API key
        self._api_key = self._get_api_key()
        
        # Initialize tokenizer
        self._tokenizer = self._initialize_tokenizer()
        
        # Create LLM client
        self._llm_client = self._create_llm_client_for_current_model()
        
        logger.info(
            f"GeminiLLM initialized. Starting with model '{self.get_current_model_name()}'"
        )
    
    def call_model(self, prompt: str) -> str:
        """Call Gemini model with retry and rotation logic."""
        initial_model_index = self._current_model_index
        first_exhaustion_error = None
        max_retries = 10
        
        for attempt in range(max_retries):
            current_model_name = self.get_current_model_name()
            logger.debug(
                f"Attempting to call model '{current_model_name}' "
                f"(Attempt {attempt + 1}/{max_retries})"
            )
            
            try:
                response = self._llm_client.invoke(prompt)
                if response.content:
                    logger.info(
                        f"Call to '{current_model_name}' successful. "
                        f"Usage: {response.usage_metadata}"
                    )
                    return response.content
                else:
                    logger.warning(
                        f"Model '{current_model_name}' returned empty response. "
                        f"Retrying in 60 seconds..."
                    )
                    time.sleep(60)
            
            except google_exceptions.ResourceExhausted as e:
                if first_exhaustion_error is None:
                    first_exhaustion_error = e
                logger.warning(f"Model '{current_model_name}' exhausted. Rotating. Error: {e}")
                self._rotate_to_next_model()
                
                if self._current_model_index == initial_model_index:
                    logger.error("All models in rotation are exhausted.")
                    raise RuntimeError("All available models are exhausted") from first_exhaustion_error
                
                self._llm_client = self._create_llm_client_for_current_model()
            
            except (
                google_exceptions.BadRequest,
                google_exceptions.PermissionDenied,
                google_exceptions.NotFound,
            ) as e:
                logger.error(f"Non-retryable API error: {e}", exc_info=True)
                raise RuntimeError(f"Non-retryable API error: {e}") from e
            
            except Exception as e:
                logger.error(f"Unexpected error: {e}", exc_info=True)
                raise RuntimeError(f"Unexpected error: {e}") from e
        
        raise RuntimeError("Failed to get valid response after multiple retries")
    
    def get_current_model_name(self) -> str:
        """Get the current model name."""
        return self.model_names[self._current_model_index]
    
    def count_tokens(self, text: str) -> int:
        """Count tokens using SentencePiece tokenizer."""
        return len(self._tokenizer.encode(text, out_type=int))
    
    def split_into_limit(
        self, text: str, language: BCP47Language = BCP47Language.ENGLISH
    ) -> List[str]:
        """Split text into chunks for translation."""
        text_splitter = NLTKTextSplitter(
            chunk_size=self._settings.llm.gemini.context_size,
            chunk_overlap=0,
            language=language.value,
            length_function=self.count_tokens,
        )
        return text_splitter.split_text(text)
    
    def _get_api_key(self) -> str:
        """Get Google API key from environment."""
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("GOOGLE_API_KEY environment variable not set")
        return api_key
    
    def _rotate_to_next_model(self) -> None:
        """Rotate to the next model in the list."""
        self._current_model_index = (self._current_model_index + 1) % len(self.model_names)
        logger.info(f"Rotated to model: '{self.get_current_model_name()}'")
    
    def _create_llm_client_for_current_model(self) -> Runnable:
        """Create LLM client for the current model."""
        model_name = self.get_current_model_name()
        config = self._settings.llm.gemini
        
        rpm = config.rate_limit
        requests_per_second = rpm / 60.0
        logger.info(f"Creating LLM client for '{model_name}' with rate limit {rpm} RPM")
        
        rate_limiter = InMemoryRateLimiter(
            requests_per_second=requests_per_second,
            max_bucket_size=config.max_bucket_size,
        )
        
        llm_client = ChatGoogleGenerativeAI(
            model=model_name,
            temperature=config.temperature,
            top_p=config.top_p,
            rate_limiter=rate_limiter,
            verbose=True,
            request_timeout=config.request_timeout,
        )
        
        return llm_client.with_retry(
            stop_after_attempt=config.retry_attempts,
            retry_if_exception_type=(
                google_exceptions.InternalServerError,
                google_exceptions.ServiceUnavailable,
                google_exceptions.DeadlineExceeded,
            ),
        )
    
    def _initialize_tokenizer(self) -> spm.SentencePieceProcessor:
        """Initialize SentencePiece tokenizer."""
        tokenizer_path = Path(self._settings.paths.tokenizer_path)
        
        if not tokenizer_path.is_file():
            logger.error(f"Tokenizer not found at: {tokenizer_path}")
            raise FileNotFoundError(f"Tokenizer not found at: {tokenizer_path}")
        
        logger.info(f"Loading tokenizer from: {tokenizer_path}")
        return spm.SentencePieceProcessor(model_file=str(tokenizer_path))
```

**Step 2: Update llm/gemini_llm.py**
```python
# llm/gemini_llm.py
"""
DEPRECATED: Use infrastructure.llm.gemini instead.
This module is kept for backward compatibility.
"""

from infrastructure.llm.gemini import GeminiLLM

__all__ = ["GeminiLLM"]
```

**Step 3: Commit**
```bash
git add infrastructure/llm/gemini.py llm/gemini_llm.py
git commit -m "feat(infrastructure): migrate GeminiLLM to new structure

- Create GeminiLLM in infrastructure/llm with Settings injection
- Add backward compatibility import in old location
- Support BCP47Language parameter in split_into_limit
- Preserve model rotation and retry logic"
```

---

## Phase 3: Services Layer

### Task 3.1: Create services package

**Files:**
- Create: `services/__init__.py`
- Create: `services/translator.py`

**Step 1: Create services directory**
```bash
mkdir -p services
```

**Step 2: Create services/__init__.py**
```python
"""Business logic services."""

from services.translator import TranslatorService, TranslationResult

__all__ = ["TranslatorService", "TranslationResult"]
```

**Step 3: Create services/translator.py**
```python
"""Translator service with dependency injection."""

import logging
import re
from dataclasses import dataclass, field
from typing import List

from config.llm import BCP47Language
from config.settings import Settings
from infrastructure.llm.factory import LLMFactory
from infrastructure.llm.protocol import LLMClient

logger = logging.getLogger(__name__)


@dataclass
class TranslationResult:
    """Result of a translation operation."""
    original_chunks: int
    translated_chunks: int
    text: str
    errors: List[str] = field(default_factory=list)
    
    @property
    def success(self) -> bool:
        """Check if translation was successful (no errors)."""
        return len(self.errors) == 0


class TranslatorService:
    """
    Service for translating text using LLM backends.
    
    Follows Single Responsibility Principle: only handles
    translation orchestration and chunk management.
    
    Usage:
        factory = LLMFactory(settings)
        translator = TranslatorService(factory)
        result = translator.translate(text, "en", "es")
    """
    
    _ERROR_CHUNK_MARKER = "[TRANSLATION_ERROR_CHUNK_{index}]"
    
    def __init__(
        self,
        llm_factory: LLMFactory,
        settings: Settings | None = None,
    ):
        """
        Initialize translator with LLM factory.
        
        Args:
            llm_factory: Factory for creating LLM clients.
            settings: Optional settings (uses Settings.get() if not provided).
        """
        self._llm_factory = llm_factory
        self._settings = settings or Settings.get()
        self._llm_client: LLMClient = llm_factory.create()
        self._progress = None
    
    def set_progress(self, progress) -> None:
        """Set progress tracker for chunk translation."""
        self._progress = progress
    
    def translate(
        self,
        text: str,
        source_lang: str,
        target_lang: str,
        language: BCP47Language = BCP47Language.ENGLISH,
    ) -> TranslationResult:
        """
        Translate text from source to target language.
        
        Args:
            text: Text to translate.
            source_lang: Source language code (e.g., "en").
            target_lang: Target language code (e.g., "es").
            language: Language for text splitting (default: English).
            
        Returns:
            TranslationResult with translated text and metadata.
        """
        # Split text into chunks
        chunks = self._llm_client.split_into_limit(text, language)
        
        logger.info(f"Text split into {len(chunks)} chunks for translation")
        
        if not chunks:
            logger.warning("No chunks to translate")
            return TranslationResult(
                original_chunks=0,
                translated_chunks=0,
                text="",
                errors=["No text to translate"],
            )
        
        # Load prompt template
        prompt_template = self._load_prompt_template()
        
        # Translate chunks
        translated_parts = []
        errors = []
        
        iterator = self._get_iterator(chunks)
        
        for i, chunk in iterator:
            try:
                result = self._translate_chunk(chunk, i, prompt_template, source_lang, target_lang)
                translated_parts.append(result)
            except Exception as e:
                logger.error(f"Error translating chunk {i + 1}: {e}")
                errors.append(f"Chunk {i + 1}: {str(e)}")
                translated_parts.append(self._ERROR_CHUNK_MARKER.format(index=i + 1))
        
        # Combine translated parts
        full_text = "\n\n".join(translated_parts)
        full_text = re.sub(r"\n{3,}", "\n\n", full_text).strip()
        
        return TranslationResult(
            original_chunks=len(chunks),
            translated_chunks=len(translated_parts),
            text=full_text,
            errors=errors,
        )
    
    def _load_prompt_template(self) -> str:
        """Load translation prompt template."""
        prompt_path = self._settings.paths.translation_prompt_path
        with open(prompt_path, "r", encoding="utf-8") as f:
            return f.read()
    
    def _translate_chunk(
        self,
        chunk: str,
        index: int,
        template: str,
        source_lang: str,
        target_lang: str,
    ) -> str:
        """Translate a single chunk."""
        prompt = template.format(
            text_chunk=chunk,
            source_lang=source_lang,
            target_lang=target_lang,
        )
        
        logger.debug(f"Chunk {index + 1}: Prompt tokens = {self._llm_client.count_tokens(prompt)}")
        
        return self._llm_client.call_model(prompt)
    
    def _get_iterator(self, chunks: List[str]):
        """Get iterator for chunk processing."""
        if self._progress:
            return self._progress(enumerate(chunks), desc="Translating Chunks...")
        return enumerate(chunks)
```

**Step 4: Commit**
```bash
git add services/
git commit -m "feat(services): add TranslatorService with dependency injection

- Create TranslatorService with LLMFactory injection
- Add TranslationResult dataclass for structured results
- Separate progress tracking from translation logic
- Support BCP47Language for text splitting"
```

---

### Task 3.2: Create GlossaryAwareTranslator service

**Files:**
- Create: `services/glossary_translator.py`

**Step 1: Create services/glossary_translator.py**
```python
"""Glossary-aware translator service."""

import logging
from typing import List

from config.llm import BCP47Language
from models.work import GlossaryEntry
from services.translator import TranslatorService, TranslationResult
from services.glossary_post_processor import GlossaryPostProcessor

logger = logging.getLogger(__name__)


class GlossaryAwareTranslator:
    """
    Translator with glossary consistency through post-processing.
    
    Instead of injecting glossary terms into the translation prompt,
    this translator applies glossary validation and correction after
    translation, ensuring 100% consistency of terms.
    
    Benefits:
    - Larger chunks (no glossary overhead in prompt)
    - Guaranteed consistency through post-processing
    - Fewer API calls for same text
    
    Usage:
        translator_service = TranslatorService(llm_factory)
        glossary_translator = GlossaryAwareTranslator(translator_service, entries)
        result = glossary_translator.translate(text, "en", "es", "es")
    """
    
    def __init__(
        self,
        translator: TranslatorService,
        glossary_entries: List[GlossaryEntry],
    ):
        """
        Initialize with translator and glossary entries.
        
        Args:
            translator: Base translator service.
            glossary_entries: List of glossary terms for post-processing.
        """
        self._translator = translator
        self._glossary_entries = glossary_entries
    
    def translate(
        self,
        text: str,
        source_lang: str,
        target_lang: str,
        target_lang_code: str,
        language: BCP47Language = BCP47Language.ENGLISH,
    ) -> TranslationResult:
        """
        Translate text with glossary post-processing.
        
        Args:
            text: Text to translate.
            source_lang: Source language code.
            target_lang: Target language code.
            target_lang_code: Target language code for glossary processing.
            language: Language for text splitting.
            
        Returns:
            TranslationResult with glossary-consistent translated text.
        """
        # Translate using base translator
        result = self._translator.translate(text, source_lang, target_lang, language)
        
        # Apply glossary post-processing
        if self._glossary_entries:
            logger.info(f"Applying glossary post-processing ({len(self._glossary_entries)} entries)")
            processor = GlossaryPostProcessor(self._glossary_entries, target_lang_code)
            result.text = processor.process(result.text)
            logger.info("Glossary post-processing completed")
        
        return result
    
    def set_progress(self, progress) -> None:
        """Set progress tracker."""
        self._translator.set_progress(progress)
```

**Step 2: Commit**
```bash
git add services/glossary_translator.py
git commit -m "feat(services): add GlossaryAwareTranslator service

- Separate from CLI commands
- Inject TranslatorService as dependency
- Apply glossary post-processing after translation
- Clean separation of concerns"
```

---

## Phase 4: Models

### Task 4.1: Create models package

**Files:**
- Create: `models/__init__.py`
- Create: `models/work.py`
- Modify: `database/models.py` (backward compatibility)

**Step 1: Create models directory**
```bash
mkdir -p models
```

**Step 2: Create models/__init__.py**
```python
"""Domain models."""

from models.work import Work, Volume, Chapter, GlossaryEntry

__all__ = ["Work", "Volume", "Chapter", "GlossaryEntry"]
```

**Step 3: Create models/work.py**
```python
"""Work-related domain models."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class Work:
    """Represents a literary work (book, light novel, etc.)."""
    
    id: Optional[int] = None
    title: str = ""
    source_lang: Optional[str] = None
    target_lang: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    def __repr__(self) -> str:
        return f"Work(id={self.id}, title='{self.title}')"


@dataclass
class Volume:
    """Represents a volume within a work."""
    
    id: Optional[int] = None
    work_id: Optional[int] = None
    volume_number: int = 0
    title: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    def __repr__(self) -> str:
        return f"Volume(id={self.id}, number={self.volume_number})"


@dataclass
class Chapter:
    """Represents a chapter within a volume."""
    
    id: Optional[int] = None
    volume_id: Optional[int] = None
    chapter_number: Optional[int] = None
    title: Optional[str] = None
    original_text: Optional[str] = None
    translated_text: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    def __repr__(self) -> str:
        if self.chapter_number:
            return f"Chapter(id={self.id}, number={self.chapter_number})"
        return f"Chapter(id={self.id}, title='{self.title}')"


@dataclass
class GlossaryEntry:
    """Represents a glossary term for translation consistency."""
    
    id: Optional[int] = None
    work_id: Optional[int] = None
    volume_id: Optional[int] = None
    source_term: str = ""
    target_term: str = ""
    context: Optional[str] = None
    notes: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    def __repr__(self) -> str:
        return f"GlossaryEntry(id={self.id}, '{self.source_term}' -> '{self.target_term}')"
```

**Step 4: Update database/models.py for backward compatibility**
```python
# database/models.py
"""
DEPRECATED: Use models.work instead.
This module is kept for backward compatibility.
"""

from models.work import Work, Volume, Chapter, GlossaryEntry

__all__ = ["Work", "Volume", "Chapter", "GlossaryEntry"]
```

**Step 5: Commit**
```bash
git add models/
git add database/models.py
git commit -m "feat(models): add models package with domain entities

- Create Work, Volume, Chapter, GlossaryEntry in models/
- Add backward compatibility import in database/models.py
- Clean separation of domain models from database layer"
```

---

## Phase 5: CLI Refactoring

### Task 5.1: Create CLI UI module

**Files:**
- Create: `cli/ui/__init__.py`
- Create: `cli/ui/selection.py`
- Create: `cli/ui/display.py`

**Step 1: Create cli/ui directory**
```bash
mkdir -p cli/ui
```

**Step 2: Create cli/ui/__init__.py**
```python
"""CLI UI components."""

from cli.ui.selection import select_work, select_volume, select_chapter, select_scope
from cli.ui.display import display_work_structure, print_summary

__all__ = [
    "select_work",
    "select_volume", 
    "select_chapter",
    "select_scope",
    "display_work_structure",
    "print_summary",
]
```

**Step 3: Create cli/ui/selection.py**
```python
"""Interactive selection components."""

from typing import Optional

import questionary

from models.work import Work, Volume, Chapter
from repositories.work import WorkRepository
from repositories.volume import VolumeRepository
from repositories.chapter import ChapterRepository


def select_work(repo: WorkRepository) -> Optional[Work]:
    """
    Interactive work selection.
    
    Args:
        repo: Work repository.
        
    Returns:
        Selected work or None if cancelled.
    """
    works = repo.get_all()
    if not works:
        return None
    
    choices = [questionary.Choice(title=w.title, value=w) for w in works]
    return questionary.select("Select a work:", choices=choices).ask()


def select_volume(work: Work, repo: VolumeRepository) -> Optional[Volume]:
    """
    Interactive volume selection.
    
    Args:
        work: Parent work.
        repo: Volume repository.
        
    Returns:
        Selected volume or None if cancelled.
    """
    if work.id is None:
        return None
    
    volumes = repo.get_by_work_id(work.id)
    if not volumes:
        return None
    
    choices = [
        questionary.Choice(
            title=f"Volume {v.volume_number}" + (f" - {v.title}" if v.title else ""),
            value=v,
        )
        for v in sorted(volumes, key=lambda vol: vol.volume_number)
    ]
    
    return questionary.select(
        f"Select a volume from '{work.title}':",
        choices=choices,
    ).ask()


def select_chapter(
    volume: Volume,
    repo: ChapterRepository,
    show_status: bool = True,
) -> Optional[Chapter]:
    """
    Interactive chapter selection.
    
    Args:
        volume: Parent volume.
        repo: Chapter repository.
        show_status: Whether to show translation status.
        
    Returns:
        Selected chapter or None if cancelled.
    """
    if volume.id is None:
        return None
    
    chapters = repo.get_by_volume(volume.id)
    if not chapters:
        return None
    
    choices = []
    for ch in sorted(chapters, key=_get_chapter_sort_key):
        status = ""
        if show_status:
            status = " [green](✓ translated)[/green]" if ch.translated_text else " [dim](○ pending)[/dim]"
        
        display = f"{_format_chapter_display(ch)}{status}"
        choices.append(questionary.Choice(title=display, value=ch))
    
    return questionary.select(
        f"Select a chapter from Volume {volume.volume_number}:",
        choices=choices,
    ).ask()


def select_scope() -> Optional[str]:
    """
    Interactive scope selection.
    
    Returns:
        Selected scope ("all_book", "all_volume", "single_chapter") or None.
    """
    return questionary.select(
        "Select translation scope:",
        choices=[
            questionary.Choice(title="All Book (translate all volumes and chapters)", value="all_book"),
            questionary.Choice(title="All Volume (translate all chapters of a volume)", value="all_volume"),
            questionary.Choice(title="Single Chapter", value="single_chapter"),
        ],
    ).ask()


def _get_chapter_sort_key(chapter: Chapter) -> tuple:
    """Get sort key for chapter ordering."""
    if chapter.chapter_number is None:
        title_lower = (chapter.title or "").lower()
        if "prologue" in title_lower:
            return (0, 0)
        elif "epilogue" in title_lower:
            return (2, 0)
        else:
            return (1, 0)
    else:
        return (1, chapter.chapter_number)


def _format_chapter_display(chapter: Chapter) -> str:
    """Format chapter for display."""
    if chapter.chapter_number is None:
        return chapter.title or "Unknown"
    else:
        title_part = f" - {chapter.title}" if chapter.title else ""
        return f"Chapter {chapter.chapter_number}{title_part}"
```

**Step 4: Create cli/ui/display.py**
```python
"""Display components for CLI."""

from rich.console import Console
from rich.table import Table

from models.work import Work, Volume, Chapter
from repositories.volume import VolumeRepository
from repositories.chapter import ChapterRepository

console = Console()


def display_work_structure(
    work: Work,
    volume_repo: VolumeRepository,
    chapter_repo: ChapterRepository,
) -> dict:
    """
    Display work structure with translation status.
    
    Args:
        work: Work to display.
        volume_repo: Volume repository.
        chapter_repo: Chapter repository.
        
    Returns:
        Dict with volume and chapter counts.
    """
    if work.id is None:
        return {"volumes": 0, "chapters": 0, "translated": 0, "pending": 0}
    
    volumes = volume_repo.get_by_work_id(work.id)
    if not volumes:
        console.print(f"[yellow]No volumes found for '{work.title}'.[/yellow]")
        return {"volumes": 0, "chapters": 0, "translated": 0, "pending": 0}
    
    total_chapters = 0
    total_translated = 0
    total_pending = 0
    
    console.print(f"\n[bold]📚 {work.title}[/bold]\n")
    
    for volume in sorted(volumes, key=lambda v: v.volume_number):
        chapters = chapter_repo.get_by_volume(volume.id) if volume.id else []
        translated = sum(1 for ch in chapters if ch.translated_text)
        pending = len(chapters) - translated
        
        total_chapters += len(chapters)
        total_translated += translated
        total_pending += pending
        
        vol_title = f" - {volume.title}" if volume.title else ""
        status = _get_volume_status(translated, len(chapters))
        
        console.print(f" [cyan]Volume {volume.volume_number}{vol_title}[/cyan]{status}")
        
        # Show first 5 chapters
        for ch in sorted(chapters, key=_get_chapter_sort_key)[:5]:
            ch_status = "[green]✓[/green]" if ch.translated_text else "[dim]○[/dim]"
            console.print(f"   {ch_status} {_format_chapter_display(ch)}")
        
        if len(chapters) > 5:
            console.print(f"   [dim]... and {len(chapters) - 5} more chapters[/dim]")
    
    console.print(f"\n[dim]Total: {len(volumes)} volumes, {total_chapters} chapters[/dim]")
    console.print(f"[dim] [green]{total_translated} translated[/green], {total_pending} pending[/dim]\n")
    
    return {
        "volumes": len(volumes),
        "chapters": total_chapters,
        "translated": total_translated,
        "pending": total_pending,
    }


def print_summary(success: int, failure: int, dry_run: bool = False) -> None:
    """
    Print translation summary table.
    
    Args:
        success: Number of successful translations.
        failure: Number of failed translations.
        dry_run: Whether this was a dry run.
    """
    table = Table(title="Translation Summary", show_header=True, header_style="bold magenta")
    table.add_column("Status", style="cyan")
    table.add_column("Count", justify="right", style="green")
    
    table.add_row("Successfully translated", str(success))
    table.add_row("Failed", str(failure))
    
    if dry_run:
        table.add_row("Mode", "[yellow]DRY-RUN (no saving)[/yellow]")
    
    console.print()
    console.print(table)


def _get_volume_status(translated: int, total: int) -> str:
    """Get status string for volume."""
    if translated == total and total > 0:
        return "[green] ✓[/green]"
    elif translated > 0:
        return f"[yellow] ({translated}/{total} translated)[/yellow]"
    elif total > 0:
        return "[dim] (pending)[/dim]"
    return ""


def _get_chapter_sort_key(chapter: Chapter) -> tuple:
    """Get sort key for chapter ordering."""
    if chapter.chapter_number is None:
        title_lower = (chapter.title or "").lower()
        if "prologue" in title_lower:
            return (0, 0)
        elif "epilogue" in title_lower:
            return (2, 0)
        else:
            return (1, 0)
    else:
        return (1, chapter.chapter_number)


def _format_chapter_display(chapter: Chapter) -> str:
    """Format chapter for display."""
    if chapter.chapter_number is None:
        return chapter.title or "Unknown"
    else:
        title_part = f" - {chapter.title}" if chapter.title else ""
        return f"Chapter {chapter.chapter_number}{title_part}"
```

**Step 5: Commit**
```bash
git add cli/ui/
git commit -m "feat(cli): add UI components module

- Create cli/ui/selection.py with interactive selection functions
- Create cli/ui/display.py with display utilities
- Separate UI logic from business logic"
```

---

## Phase 6: Legacy Code Removal

### Task 6.1: Remove unused files

**Files:**
- Delete: `tools/GeminiTextToSpeech.py`
- Delete: `tools/DocumentTextExtractor.py`
- Delete: `reviewer/` directory
- Delete: `database/schemas/` directory

**Step 1: Verify GeminiTextToSpeech.py is unused**
```bash
grep -r "GeminiTextToSpeech" --include="*.py" . 2>/dev/null | grep -v "Binary file"
```

**Step 2: Verify DocumentTextExtractor.py is unused**
```bash
grep -r "DocumentTextExtractor" --include="*.py" . 2>/dev/null | grep -v "Binary file"
```

**Step 3: Remove files**
```bash
rm -f tools/GeminiTextToSpeech.py
rm -f tools/DocumentTextExtractor.py
rm -rf reviewer/
rm -rf database/schemas/
```

**Step 4: Commit**
```bash
git add -A
git commit -m "chore: remove unused legacy files

- Remove tools/GeminiTextToSpeech.py (not integrated)
- Remove tools/DocumentTextExtractor.py (duplicate of TextExtractor)
- Remove reviewer/ directory (use tempfile instead)
- Remove database/schemas/ (empty, using models/)"
```

---

### Task 6.2: Fix duplicate code in AudioGenerator.py

**Files:**
- Modify: `tools/AudioGenerator.py`

**Step 1: Identify duplicate function**
Lines 13-41 and 62-92 contain duplicate `_ensure_nltk_punkt` function.

**Step 2: Remove duplicate (keep one definition after imports)**
```python
# After fixing, the file should have _ensure_nltk_punkt defined once
# around line 13-30
```

**Step 3: Commit**
```bash
git add tools/AudioGenerator.py
git commit -m "fix: remove duplicate _ensure_nltk_punkt function in AudioGenerator"
```

---

### Task 6.3: Fix dead code in translate_chapter.py

**Files:**
- Modify: `cli/commands/translate_chapter.py`

**Step 1: Remove duplicate raise typer.Exit(0) at line 696-697**

**Step 2: Commit**
```bash
git add cli/commands/translate_chapter.py
git commit -m "fix: remove dead code (duplicate typer.Exit) in translate_chapter"
```

---

## Phase 7: Final Validation

### Task 7.1: Update imports across codebase

**Step 1: Find all imports from old locations**
```bash
grep -r "from GlobalConfig import" --include="*.py" . | head -20
grep -r "from llm\." --include="*.py" . | head -20
grep -r "from database.models import" --include="*.py" . | head -20
```

**Step 2: Update imports to use new locations**
- Update `GlobalConfig` imports to use backward compatibility wrapper (already done)
- Update `llm.*` imports to use `infrastructure.llm.*` (backward compat exists)
- Update `database.models` imports to use `models.work` (backward compat exists)

**Step 3: Verify all imports work**
```bash
python -c "
from config.settings import Settings
from infrastructure.llm.factory import LLMFactory
from services.translator import TranslatorService
from models.work import Work, Volume, Chapter, GlossaryEntry
print('All imports OK')
"
```

**Step 4: Commit**
```bash
git add -A
git commit -m "refactor: update imports to use new module structure

- GlobalConfig imports use backward compat wrapper
- LLM imports use infrastructure.llm.*
- Model imports use models.work
- Services use new locations"
```

---

### Task 7.2: Run tests and fix failures

**Step 1: Run test suite**
```bash
pytest tests/ -v --tb=short 2>&1 | tail -50
```

**Step 2: Fix any import errors or test failures**

**Step 3: Commit fixes**
```bash
git add -A
git commit -m "fix: resolve test failures after refactoring"
```

---

### Task 7.3: Update documentation

**Files:**
- Create: `docs/architecture.md`

**Step 1: Create architecture documentation**
```bash
# Document the new structure, module responsibilities, and design decisions
```

**Step 2: Commit**
```bash
git add docs/
git commit -m "docs: add architecture documentation"
```

---

## Summary

| Phase | Description | Tasks |
|-------|-------------|-------|
| 1 | Configuration System | 2 |
| 2 | LLM Infrastructure | 4 |
| 3 | Services Layer | 2 |
| 4 | Models | 1 |
| 5 | CLI Refactoring | 1 |
| 6 | Legacy Removal | 3 |
| 7 | Final Validation | 3 |

**Total Tasks:** 16

**Estimated Duration:** 8-12 days

**Key Benefits:**
- Pydantic Settings with validation
- Factory Pattern for LLM creation
- Dependency Injection throughout
- Clean separation of concerns
- Type safety with protocols
- Removed ~500 lines of legacy/duplicate code
