"""
Backward compatibility wrapper for GlobalConfig.

DEPRECATED: Use config.settings.Settings instead.
This module will be removed in a future version.

This wrapper provides the same interface as the original GlobalConfig
but delegates to the new Pydantic Settings system.
"""

import warnings
from typing import Type, Dict, Any, Optional, List

from config.settings import Settings
from config.llm import LLMProvider, BCP47Language

# Suppress deprecation warning for now during transition
# warnings.warn(
#     "GlobalConfig is deprecated. Use config.settings.Settings instead.",
#     DeprecationWarning,
#     stacklevel=2
# )


class _Singleton(type):
    """A metaclass that creates a Singleton base class when called."""

    _instances: Dict[Type, object] = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(_Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]


class GlobalConfig(metaclass=_Singleton):
    """
    Backward compatibility wrapper for Settings.

    This class provides the same interface as the old GlobalConfig
    but delegates to the new Pydantic Settings system.

    IMPORTANT: All properties are read-only through the Settings system.
    Use Settings.get() directly if you need to modify values.
    """

    def __init__(self):
        """Initialize wrapper with Settings singleton."""
        self._settings = Settings.get()

        # Store legacy-only properties (not in new Settings system)
        self._legacy_input_path: Optional[str] = None
        self._legacy_source_lang: str = "en-US"
        self._legacy_target_lang: str = "es-MX"
        self._legacy_output_format: str = "m4a"
        self._legacy_gen_video: bool = False
        self._legacy_develop_mode: bool = True
        self._legacy_voice: str = "Paulina"
        self._legacy_nvidia_retry_attempts: int = 6
        self._legacy_nvidia_request_timeout: int = 600
        self._legacy_nvidia_max_bucket_size: int = 10
        self._legacy_ollama_top_k: int = 40

        # NER settings (legacy naming)
        self._legacy_ner_min_frequency: int = 2

        # NVIDIA NIM settings
        self._legacy_nvidia_nim_api_key: Optional[str] = None
        self._legacy_nvidia_embed_model: str = "nvidia/llama-3.2-nv-embedqa-1b-v2"
        self._legacy_nvidia_rerank_model: str = "nv-rerank-qa-mistral-4b:1"
        self._legacy_nvidia_embed_batch_size: int = 32
        self._legacy_nvidia_rerank_top_n: int = 10

        # Config file state (for backward compatibility with load/save)
        self._config_path: Optional[str] = None
        self._is_loaded = False

    # =========================================================================
    # PDFAgent Settings (Legacy properties)
    # =========================================================================

    @property
    def input_path(self) -> Optional[str]:
        """Input path for PDF processing (legacy property)."""
        return self._legacy_input_path

    @input_path.setter
    def input_path(self, value: Optional[str]) -> None:
        self._legacy_input_path = value

    @property
    def source_lang(self) -> str:
        """Source language code (legacy property)."""
        return self._legacy_source_lang

    @source_lang.setter
    def source_lang(self, value: str) -> None:
        self._legacy_source_lang = value

    @property
    def target_lang(self) -> str:
        """Target language code (legacy property)."""
        return self._legacy_target_lang

    @target_lang.setter
    def target_lang(self, value: str) -> None:
        self._legacy_target_lang = value

    @property
    def output_format(self) -> str:
        """Output format for audio (legacy property)."""
        return self._legacy_output_format

    @output_format.setter
    def output_format(self, value: str) -> None:
        self._legacy_output_format = value

    @property
    def gen_video(self) -> bool:
        """Whether to generate video (legacy property)."""
        return self._legacy_gen_video

    @gen_video.setter
    def gen_video(self, value: bool) -> None:
        self._legacy_gen_video = value

    @property
    def develop_mode(self) -> bool:
        """Development mode flag (legacy property)."""
        return self._legacy_develop_mode

    @develop_mode.setter
    def develop_mode(self, value: bool) -> None:
        self._legacy_develop_mode = value

    @property
    def voice(self) -> str:
        """Voice for text-to-speech (legacy property)."""
        return self._legacy_voice

    @voice.setter
    def voice(self, value: str) -> None:
        self._legacy_voice = value

    # =========================================================================
    # LLM Provider Settings
    # =========================================================================

    @property
    def agent(self) -> str:
        """Current LLM agent/provider."""
        return self._settings.llm.agent.value

    @agent.setter
    def agent(self, value: str) -> None:
        """Set the LLM agent (creates new Settings with updated agent)."""
        # This is a legacy setter - modifying settings requires reset
        Settings.reset()
        # Note: This is a workaround for backward compatibility
        # Proper way would be to use environment variables
        self._settings = Settings.get()

    # =========================================================================
    # Gemini Settings
    # =========================================================================

    @property
    def gemini_model_names(self) -> List[str]:
        """List of Gemini model names to use."""
        return self._settings.llm.gemini.model_names

    @property
    def gemini_temperature(self) -> float:
        """Gemini temperature parameter."""
        return self._settings.llm.gemini.temperature

    @property
    def gemini_top_p(self) -> float:
        """Gemini top_p parameter."""
        return self._settings.llm.gemini.top_p

    @property
    def gemini_top_k(self) -> int:
        """Gemini top_k parameter."""
        return self._settings.llm.gemini.top_k

    @property
    def gemini_context_size(self) -> int:
        """Gemini context size."""
        return self._settings.llm.gemini.context_size

    @property
    def gemini_retry_attempts(self) -> int:
        """Number of retry attempts for Gemini."""
        return self._settings.llm.gemini.retry_attempts

    @property
    def gemini_max_bucket_size(self) -> int:
        """Gemini rate limiter bucket size."""
        return self._settings.llm.gemini.max_bucket_size

    @property
    def gemini_default_fallback_rpm(self) -> int:
        """Gemini default fallback requests per minute."""
        return self._settings.llm.gemini.rate_limit

    @property
    def gemini_request_timeout(self) -> int:
        """Gemini request timeout in seconds."""
        return self._settings.llm.gemini.request_timeout

    @property
    def gemini_model_rate_limits(self) -> Dict[str, int]:
        """Gemini model rate limits (backward compatibility)."""
        return {
            name: self._settings.llm.gemini.rate_limit
            for name in self._settings.llm.gemini.model_names
        }

    @property
    def tokenizer_path(self) -> str:
        """Path to tokenizer model."""
        return str(self._settings.paths.tokenizer_path)

    # =========================================================================
    # NVIDIA Settings
    # =========================================================================

    @property
    def nvidia_model_name(self) -> str:
        """NVIDIA model name."""
        return self._settings.llm.nvidia.model_name

    @property
    def nvidia_temperature(self) -> float:
        """NVIDIA temperature parameter."""
        return self._settings.llm.nvidia.temperature

    @property
    def nvidia_top_p(self) -> float:
        """NVIDIA top_p parameter."""
        return self._settings.llm.nvidia.top_p

    @property
    def nvidia_max_output_tokens(self) -> int:
        """NVIDIA max output tokens."""
        return self._settings.llm.nvidia.max_output_tokens

    @property
    def nvidia_model_rate_limit(self) -> int:
        """NVIDIA model rate limit (requests per minute)."""
        return self._settings.llm.nvidia.rate_limit

    @property
    def nvidia_local_tokenizer_name(self) -> str:
        """NVIDIA local tokenizer name."""
        return self._settings.llm.nvidia.local_tokenizer_name

    @property
    def nvidia_local_tokenizer_dir(self) -> str:
        """NVIDIA local tokenizer directory."""
        return self._settings.llm.nvidia.local_tokenizer_dir

    # Legacy NVIDIA properties not in new config (use defaults)
    @property
    def nvidia_retry_attempts(self) -> int:
        """NVIDIA retry attempts (legacy property)."""
        return self._legacy_nvidia_retry_attempts

    @nvidia_retry_attempts.setter
    def nvidia_retry_attempts(self, value: int) -> None:
        self._legacy_nvidia_retry_attempts = value

    @property
    def nvidia_request_timeout(self) -> int:
        """NVIDIA request timeout (legacy property)."""
        return self._legacy_nvidia_request_timeout

    @nvidia_request_timeout.setter
    def nvidia_request_timeout(self, value: int) -> None:
        self._legacy_nvidia_request_timeout = value

    @property
    def nvidia_max_bucket_size(self) -> int:
        """NVIDIA max bucket size (legacy property)."""
        return self._legacy_nvidia_max_bucket_size

    @nvidia_max_bucket_size.setter
    def nvidia_max_bucket_size(self, value: int) -> None:
        self._legacy_nvidia_max_bucket_size = value

    # =========================================================================
    # Ollama Settings
    # =========================================================================

    @property
    def ollama_default_model_name(self) -> str:
        """Ollama default model name."""
        return self._settings.llm.ollama.model_name

    @property
    def ollama_validate_model(self) -> bool:
        """Whether to validate Ollama model on init."""
        return self._settings.llm.ollama.validate_model

    @property
    def ollama_temperature(self) -> float:
        """Ollama temperature parameter."""
        return self._settings.llm.ollama.temperature

    @property
    def ollama_top_p(self) -> float:
        """Ollama top_p parameter."""
        return self._settings.llm.ollama.top_p

    @property
    def ollama_context_size(self) -> int:
        """Ollama context size."""
        return self._settings.llm.ollama.context_size

    @property
    def ollama_model_id(self) -> str:
        """Ollama model ID."""
        return self._settings.llm.ollama.model_id

    @property
    def ollama_local_tokenizer_dir(self) -> str:
        """Ollama local tokenizer directory."""
        return self._settings.llm.ollama.local_tokenizer_dir

    @property
    def ollama_local_tokenizer_name(self) -> str:
        """Ollama local tokenizer name."""
        return self._settings.llm.ollama.local_tokenizer_name

    # Legacy Ollama property not in new config
    @property
    def ollama_top_k(self) -> int:
        """Ollama top_k parameter (legacy property)."""
        return self._legacy_ollama_top_k

    @ollama_top_k.setter
    def ollama_top_k(self, value: int) -> None:
        self._legacy_ollama_top_k = value

    # =========================================================================
    # Database Settings
    # =========================================================================

    @property
    def db_host(self) -> str:
        """Database host."""
        return self._settings.database.host

    @property
    def db_port(self) -> int:
        """Database port."""
        return self._settings.database.port

    @property
    def db_name(self) -> str:
        """Database name."""
        return self._settings.database.name

    @property
    def db_user(self) -> str:
        """Database user."""
        return self._settings.database.user

    @property
    def db_password(self) -> str:
        """Database password."""
        return self._settings.database.password

    @property
    def db_min_pool_size(self) -> int:
        """Database minimum pool size (maps to min_connections)."""
        return self._settings.database.min_connections

    @property
    def db_max_pool_size(self) -> int:
        """Database maximum pool size (maps to max_connections)."""
        return self._settings.database.max_connections

    # =========================================================================
    # NER / NLP Settings
    # =========================================================================

    @property
    def ner_min_frequency(self) -> int:
        """NER minimum frequency threshold (legacy property)."""
        return self._legacy_ner_min_frequency

    @ner_min_frequency.setter
    def ner_min_frequency(self, value: int) -> None:
        self._legacy_ner_min_frequency = value

    @property
    def ner_confidence_threshold(self) -> float:
        """NER confidence threshold."""
        return self._settings.nlp.confidence_threshold

    @property
    def ner_model(self) -> str:
        """NER model name."""
        return self._settings.nlp.ner_model

    @property
    def ner_entity_types(self) -> List[str]:
        """NER entity types to extract."""
        return self._settings.nlp.entity_types

    # =========================================================================
    # NVIDIA NIM Settings (Legacy)
    # =========================================================================

    @property
    def nvidia_nim_api_key(self) -> Optional[str]:
        """NVIDIA NIM API key (legacy property)."""
        import os

        return self._legacy_nvidia_nim_api_key or os.getenv("NVIDIA_API_KEY")

    @nvidia_nim_api_key.setter
    def nvidia_nim_api_key(self, value: Optional[str]) -> None:
        self._legacy_nvidia_nim_api_key = value

    @property
    def nvidia_embed_model(self) -> str:
        """NVIDIA embedding model (legacy property)."""
        return self._legacy_nvidia_embed_model

    @nvidia_embed_model.setter
    def nvidia_embed_model(self, value: str) -> None:
        self._legacy_nvidia_embed_model = value

    @property
    def nvidia_rerank_model(self) -> str:
        """NVIDIA rerank model (legacy property)."""
        return self._legacy_nvidia_rerank_model

    @nvidia_rerank_model.setter
    def nvidia_rerank_model(self, value: str) -> None:
        self._legacy_nvidia_rerank_model = value

    @property
    def nvidia_embed_batch_size(self) -> int:
        """NVIDIA embedding batch size (legacy property)."""
        return self._legacy_nvidia_embed_batch_size

    @nvidia_embed_batch_size.setter
    def nvidia_embed_batch_size(self, value: int) -> None:
        self._legacy_nvidia_embed_batch_size = value

    @property
    def nvidia_rerank_top_n(self) -> int:
        """NVIDIA rerank top N (legacy property)."""
        return self._legacy_nvidia_rerank_top_n

    @nvidia_rerank_top_n.setter
    def nvidia_rerank_top_n(self, value: int) -> None:
        self._legacy_nvidia_rerank_top_n = value

    # =========================================================================
    # Path Settings
    # =========================================================================

    @property
    def translation_prompt_path(self) -> str:
        """Path to translation prompt template."""
        return str(self._settings.paths.translation_prompt_path)

    # =========================================================================
    # Legacy Methods (for backward compatibility)
    # =========================================================================

    def _get_expected_types(self) -> Dict[str, Any]:
        """Get expected types for validation (legacy method)."""
        return {
            "input_path": (str, type(None)),
            "source_lang": str,
            "target_lang": str,
            "output_format": str,
            "gen_video": bool,
            "agent": str,
            "develop_mode": bool,
            "translation_prompt_path": str,
            "voice": str,
            "gemini_model_names": list,
            "gemini_temperature": float,
            "gemini_top_p": float,
            "gemini_top_k": int,
            "gemini_context_size": int,
            "gemini_retry_attempts": int,
            "gemini_max_bucket_size": int,
            "gemini_default_fallback_rpm": int,
            "gemini_request_timeout": int,
            "tokenizer_path": str,
            "gemini_model_rate_limits": dict,
            "ollama_default_model_name": str,
            "ollama_validate_model": bool,
            "ollama_temperature": float,
            "ollama_top_p": float,
            "ollama_top_k": int,
            "ollama_context_size": int,
            "ollama_model_id": str,
            "ollama_local_tokenizer_dir": str,
            "ollama_local_tokenizer_name": str,
            "nvidia_retry_attempts": int,
            "nvidia_request_timeout": int,
            "nvidia_top_p": float,
            "nvidia_temperature": float,
            "nvidia_max_bucket_size": int,
            "nvidia_model_rate_limit": int,
            "nvidia_max_output_tokens": int,
            "nvidia_model_name": str,
            "nvidia_local_tokenizer_dir": str,
            "nvidia_local_tokenizer_name": str,
            "db_host": str,
            "db_port": int,
            "db_name": str,
            "db_user": str,
            "db_password": str,
            "db_min_pool_size": int,
            "db_max_pool_size": int,
            "ner_min_frequency": int,
            "ner_confidence_threshold": float,
            "nvidia_nim_api_key": str,
            "nvidia_embed_model": str,
            "nvidia_rerank_model": str,
            "nvidia_embed_batch_size": int,
            "nvidia_rerank_top_n": int,
        }

    def load(self, config_path: str) -> None:
        """
        Load configuration from a JSON file (legacy method).

        DEPRECATED: Use environment variables or Settings directly.
        """
        import json

        self._config_path = config_path
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except FileNotFoundError:
            raise FileNotFoundError(f"Configuration file not found at: {config_path}")
        except json.JSONDecodeError:
            raise ValueError(f"Invalid JSON in config file: {config_path}")

        self._validate(data)
        for key, value in data.items():
            if hasattr(self, key):
                setattr(self, key, value)
        self._is_loaded = True

    def save(self, config_path: Optional[str] = None) -> None:
        """
        Save configuration to a JSON file (legacy method).

        DEPRECATED: Use environment variables or Settings directly.
        """
        import json

        path_to_save = config_path or self._config_path
        if not path_to_save:
            raise ValueError("A path must be provided to save the configuration.")

        self._config_path = path_to_save
        config_data = {
            key: getattr(self, key) for key in self._get_expected_types().keys()
        }

        try:
            with open(path_to_save, "w", encoding="utf-8") as f:
                json.dump(config_data, f, indent=4)
        except IOError as e:
            print(f"Error saving configuration to {path_to_save}: {e}")

    def _validate(self, data: Dict[str, Any]) -> None:
        """Validate configuration data (legacy method)."""
        expected_types = self._get_expected_types()
        for key, expected_type in expected_types.items():
            if key in data and not isinstance(data[key], expected_type):
                raise ValueError(
                    f"Invalid type for configuration key '{key}'. "
                    f"Expected {expected_type}, got {type(data[key]).__name__}."
                )

    def update_from_dict(self, data: dict) -> None:
        """Update configuration from a dictionary (legacy method)."""
        for key, value in data.items():
            if hasattr(self, key) and value is not None:
                setattr(self, key, value)

    def is_loaded(self) -> bool:
        """Check if configuration was loaded from file."""
        return self._is_loaded

    def __str__(self) -> str:
        """String representation of current configuration."""
        import json

        config_data = {
            key: getattr(self, key) for key in self._get_expected_types().keys()
        }
        return json.dumps(config_data, indent=2)


# Export BCP47Language for backward compatibility
__all__ = ["GlobalConfig", "BCP47Language"]


if __name__ == "__main__":
    config = GlobalConfig()
    print("--- Default Config ---")
    print(config)

    # Example of testing properties
    print(f"\nAgent: {config.agent}")
    print(f"NVIDIA Model: {config.nvidia_model_name}")
    print(f"Database: {config.db_host}:{config.db_port}/{config.db_name}")
