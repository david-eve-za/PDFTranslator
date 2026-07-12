"""LLM configuration models."""

from enum import Enum
from typing import Dict

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


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

    def to_nltk_name(self) -> str:
        """
        Convert BCP 47 code to NLTK language name.

        NLTK requires full language names like 'english', 'spanish', etc.
        not BCP 47 codes like 'en', 'es'.

        Returns:
            NLTK-compatible language name string.
        """
        nltk_names = {
            "en": "english",
            "es": "spanish",
            "zh": "chinese",
            "ja": "japanese",
            "ko": "korean",
            "fr": "french",
            "de": "german",
            "it": "italian",
            "pt": "portuguese",
            "ru": "russian",
            "ar": "arabic",
            "hi": "hindi",
        }
        return nltk_names.get(self.value, "english")


class GeminiConfig(BaseModel):
    """Google Gemini configuration."""

    model_names: list[str] = Field(
        default_factory=lambda: ["gemini-2.0-flash"],
        description="List of Gemini model names to use",
    )
    temperature: float = Field(default=0.3, ge=0.0, le=2.0)
    top_p: float = Field(default=0.95, ge=0.0, le=1.0)
    top_k: int = Field(default=40, ge=1)
    context_size: int = Field(default=1000000, gt=0)
    rate_limit: int = Field(default=15, gt=0, description="Requests per minute")
    max_bucket_size: int = Field(default=10, gt=0)
    request_timeout: int = Field(
        default=3600, gt=0, description="Request timeout in seconds"
    )
    retry_attempts: int = Field(default=3, gt=0)


class NvidiaConfig(BaseSettings):
    """NVIDIA NIM configuration."""

    model_config = SettingsConfigDict(
        env_prefix="LLM__NVIDIA__",
        env_nested_delimiter="__",
    )

    model_name: str = Field(default="mistralai/mistral-large-3-675b-instruct-2512")
    temperature: float = Field(default=0.2, ge=0.0, le=2.0)
    top_p: float = Field(default=0.95, ge=0.0, le=1.0)
    max_output_tokens: int = Field(
        default=8192,
        ge=1024,
        le=131072,
        description="Max tokens reserved for model output per request"
    )
    rate_limit: int = Field(default=30, gt=0, description="Requests per minute")
    retry_attempts: int = Field(default=6, gt=0)
    request_timeout: int = Field(
        default=3600, gt=0, description="Request timeout in seconds"
    )
    max_bucket_size: int = Field(default=10, gt=0)
    context_size: int = Field(
        default=131072,
        frozen=True,
        description="Model context window (input + output)"
    )
    chunk_safety_margin_pct: float = Field(
        default=0.15,
        ge=0.05,
        le=0.30,
        description="Percentage margin to prevent truncation"
    )
    max_chunk_tokens: int = Field(
        default=32768,
        ge=512,
        le=65536,
        description="Practical upper bound per chunk"
    )
    min_chunk_tokens: int = Field(
        default=512,
        ge=128,
        description="Minimum viable chunk size"
    )
    local_tokenizer_name: str = Field(
        default="mistralai/Mistral-Large-3-675B-Instruct-2512"
    )
    local_tokenizer_dir: str = Field(default="mistral-large-3-675b-instruct-2512")
    # NVIDIA NIM Embedding/Reranking settings
    embed_model: str = Field(default="nvidia/nv-embedqa-e5-v5")
    rerank_model: str = Field(default="nvidia/nv-rerankqa-mistral-2b-4b-4096-v1")
    rerank_top_n: int = Field(default=5, gt=0)
    # NEW: Custom expansion ratios per language pair
    expansion_ratios: Dict[str, float] = Field(
        default_factory=dict,
        description="Custom ratios: 'en-es': 1.3, 'en-zh': 0.6, etc."
    )


class OllamaConfig(BaseModel):
    """Ollama local LLM configuration."""

    model_name: str = Field(default="llama3.2")
    temperature: float = Field(default=0.3, ge=0.0, le=2.0)
    top_p: float = Field(default=0.9, ge=0.0, le=1.0)
    context_size: int = Field(default=4096, gt=0)
    validate_model: bool = Field(default=True)
    # Matches llama3.2 (different from llama3.1)
    local_tokenizer_name: str = Field(default="meta-llama/Llama-3.2-1B")
    local_tokenizer_dir: str = Field(default=".tokenizers/ollama")
    model_id: str = Field(default="meta-llama/Llama-3.1-8B-Instruct")


class LLMSettings(BaseModel):
    """LLM settings aggregating all provider configs."""

    agent: LLMProvider = Field(default=LLMProvider.NVIDIA)
    gemini: GeminiConfig = Field(default_factory=GeminiConfig)
    nvidia: NvidiaConfig = Field(default_factory=NvidiaConfig)
    ollama: OllamaConfig = Field(default_factory=OllamaConfig)
    # API keys (loaded from environment)
    nvidia_api_key: str = Field(default="", description="NVIDIA NIM API key")
    google_api_key: str = Field(default="", description="Google/Gemini API key")

    def get_config_for_provider(
        self, provider: LLMProvider
    ) -> GeminiConfig | NvidiaConfig | OllamaConfig:
        """Get configuration for a specific provider."""
        configs = {
            LLMProvider.GEMINI: self.gemini,
            LLMProvider.NVIDIA: self.nvidia,
            LLMProvider.OLLAMA: self.ollama,
        }
        return configs[provider]
