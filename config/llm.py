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
        description="List of Gemini model names to use",
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
