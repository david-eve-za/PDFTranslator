import logging
from pathlib import Path
from typing import List

from langchain_nvidia_ai_endpoints import ChatNVIDIA
from langchain_text_splitters import NLTKTextSplitter
from transformers import AutoTokenizer

from GlobalConfig import GlobalConfig
from LLM.llm_service import LLMService


class NvidiaAI(LLMService):
    """NVIDIA NIM cloud API connector using langchain-nvidia-ai-endpoints."""

    def __init__(self):
        self._logger = logging.getLogger(__name__)
        self.config = GlobalConfig()
        self._tokenizer = self._download_and_cache_tokenizer()
        self._model = ChatNVIDIA(
            model=self.config.nvidia_model_name,
            temperature=self.config.nvidia_temperature,
            top_p=self.config.nvidia_top_p,
            verbose=True,
        )
        self._logger.info(
            f"NvidiaAI initialized with model: {self.config.nvidia_model_name}"
        )

    def call_model(self, prompt: str) -> str:
        response = self._model.invoke(prompt)
        self._logger.info(
            f"Call to '{self.get_current_model_name()}' successful. Usage: {response.usage_metadata}"
        )
        return response.content

    def get_current_model_name(self) -> str:
        return self.config.nvidia_model_name

    def count_tokens(self, text: str) -> int:
        token_ids = self._tokenizer.encode(text, add_special_tokens=False)
        return len(token_ids)

    def split_into_limit(self, text: str) -> List[str]:
        pass

    def _download_and_cache_tokenizer(self):
        """
        Downloads and caches the tokenizer if it doesn't already exist locally.
        """
        tokenizer_dir = Path(self.config.nvidia_local_tokenizer_dir)
        if tokenizer_dir.exists():
            self._logger.info(f"Tokenizer already cached in {tokenizer_dir}")
        else:
            self._logger.info(
                f"Downloading tokenizer for {self.config.nvidia_local_tokenizer_name}..."
            )
            tokenizer = AutoTokenizer.from_pretrained(
                self.config.nvidia_local_tokenizer_name, use_fast=True
            )
            tokenizer_dir.mkdir(parents=True, exist_ok=True)
            tokenizer.save_pretrained(tokenizer_dir)
            self._logger.info(f"Tokenizer saved in {tokenizer_dir}")

        return AutoTokenizer.from_pretrained(tokenizer_dir, use_fast=True)
