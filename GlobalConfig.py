import json
import os
from typing import Type, Dict, Any, Optional, List


class _Singleton(type):
    """A metaclass that creates a Singleton base class when called."""

    _instances: Dict[Type, object] = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(_Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]


class GlobalConfig(metaclass=_Singleton):
    """
    A singleton class to manage global configurations for the application.
    It supports loading from and saving to a JSON file, data validation, and typed properties.
    """

    def __init__(self):
        # --- Default Configurations with Type Hinting ---
        # PDFAgent settings
        self.input_path: Optional[str] = None
        self.source_lang: str = "en-US"
        self.target_lang: str = "es-MX"
        self.output_format: str = "m4a"
        self.gen_video: bool = False
        self.agent: str = "nvidia"  # Main agent selector ('gemini', 'ollama')
        self.develop_mode: bool = True

        # Tool settings
        self.translation_prompt_path: str = "tools/translation_prompt.txt"
        self.voice: str = "Paulina"

        # GeminiLLM settings
        self.gemini_model_names: List[str] = ["gemma-3-27b-it"]
        self.gemini_temperature: float = 0.2
        self.gemini_top_p: float = 0.95
        self.gemini_top_k: int = 40
        self.gemini_retry_attempts: int = 6
        self.gemini_max_bucket_size: int = 10
        self.gemini_default_fallback_rpm: int = 15
        self.gemini_context_size: int = 1500
        self.gemini_request_timeout: int = 600
        self.tokenizer_path: str = "models/tokenizer.model"
        self.gemini_model_rate_limits: Dict[str, int] = {
            "gemma-3-27b-it": 5,
        }

        # OllamaLLM settings
        self.ollama_default_model_name: str = "aya-expanse:32b"
        self.ollama_validate_model: bool = True
        self.ollama_temperature: float = 0.2
        self.ollama_top_p: float = 0.95
        self.ollama_top_k: int = 40
        self.ollama_context_size: int = 3000
        self.ollama_model_id: str = "CohereLabs/aya-expanse-32b"
        self.ollama_local_tokenizer_dir: str = "tokenizer_aya-expanse"
        self.ollama_local_tokenizer_name: str = "openai/gpt-oss-120b"

        # NvidiaLLM settings
        self.nvidia_retry_attempts = 6
        self.nvidia_request_timeout = 600
        self.nvidia_top_p = 0.95
        self.nvidia_temperature = 0.2
        self.nvidia_max_bucket_size = 10
        self.nvidia_model_rate_limit = 30
        self.nvidia_max_output_tokens = 4096
        self.nvidia_model_name = "mistralai/mistral-large-3-675b-instruct-2512"
        self.nvidia_local_tokenizer_dir: str = "mistral-large-3-675b-instruct-2512"
        self.nvidia_local_tokenizer_name: str = (
            "mistralai/Mistral-Large-3-675B-Instruct-2512"
        )

        # Database settings
        self.db_host: str = "localhost"
        self.db_port: int = 5432
        self.db_name: str = "book_translator"
        self.db_user: str = "translator_user"
        self.db_password: str = 'uQ201/-R]f3"j@]N7/L:'
        self.db_min_pool_size: int = 2
        self.db_max_pool_size: int = 10

        # NER / Entity extraction settings
        self.ner_min_frequency: int = 2
        self.ner_confidence_threshold: float = 0.5

        # NVIDIA NIM settings for embeddings and reranking
        self.nvidia_nim_api_key: str = os.getenv("NVIDIA_API_KEY")
        self.nvidia_embed_model: str = "nvidia/llama-3.2-nv-embedqa-1b-v2"
        self.nvidia_rerank_model: str = "nv-rerank-qa-mistral-4b:1"
        self.nvidia_embed_batch_size: int = 32
        self.nvidia_rerank_top_n: int = 10

        # --- Internal State ---
        self._config_path: Optional[str] = None
        self._is_loaded = False

    def _get_expected_types(self) -> Dict[str, Any]:
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

    def _validate(self, data: Dict[str, Any]) -> None:
        """Validates the configuration data."""
        expected_types = self._get_expected_types()

        for key, expected_type in expected_types.items():
            if key in data and not isinstance(data[key], expected_type):
                raise ValueError(
                    f"Invalid type for configuration key '{key}'. "
                    f"Expected {expected_type}, got {type(data[key]).__name__}."
                )

    def load(self, config_path: str) -> None:
        """Loads configuration from a JSON file."""
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
        """Saves the current configuration to a JSON file."""
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

    def update_from_dict(self, data: dict) -> None:
        """Updates configuration from a dictionary."""
        for key, value in data.items():
            if hasattr(self, key) and value is not None:
                setattr(self, key, value)

    def is_loaded(self) -> bool:
        return self._is_loaded

    def __str__(self) -> str:
        """String representation of the current configuration."""
        config_data = {
            key: getattr(self, key) for key in self._get_expected_types().keys()
        }
        return json.dumps(config_data, indent=2)


if __name__ == "__main__":
    config = GlobalConfig()
    print("--- Default Config ---")
    print(config)

    # Example of saving the default config
    CONFIG_FILE = "config.json.example"
    print(f"\n--- Saving example config to {CONFIG_FILE} ---")
    config.save(CONFIG_FILE)

    # Example of loading and modifying
    config.load(CONFIG_FILE)
    config.agent = "ollama"
    print("\n--- Modified Config ---")
    print(config)

    if os.path.exists(CONFIG_FILE):
        os.remove(CONFIG_FILE)
