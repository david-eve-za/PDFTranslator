import logging
from pathlib import Path
from typing import List
from langchain_ollama import ChatOllama
from langchain_text_splitters import NLTKTextSplitter
from transformers import AutoTokenizer

from GlobalConfig import GlobalConfig
from llm.base_llm import BaseLLM


class OllamaLLM(BaseLLM):
    """Ollama local LLM connector using langchain-ollama."""

    def __init__(self):
        self._logger = logging.getLogger(__name__)
        self.config = GlobalConfig()
        self._tokenizer = self._download_and_cache_tokenizer()
        self._model = ChatOllama(
            model=self.config.ollama_default_model_name,
            validate_model_on_init=self.config.ollama_validate_model,
            temperature=self.config.ollama_temperature,
            top_p=self.config.ollama_top_p,
            # top_k=self.config.ollama_top_k,
            verbose=True,
            reasoning=False,
        )

    def call_model(self, prompt: str) -> str:
        response = self._model.invoke(prompt)
        self._logger.info(
            f"Call to '{self.get_current_model_name()}' successful. Usage: {response.usage_metadata}"
        )
        return response.content

    def get_current_model_name(self) -> str:
        return self.config.ollama_default_model_name

    def count_tokens(self, text: str) -> int:
        token_ids = self._tokenizer.encode(text, add_special_tokens=False)
        return len(token_ids)

    def split_into_limit(self, text: str) -> List[str]:
        text_spliter = NLTKTextSplitter(
            chunk_size=self.config.ollama_context_size,
            chunk_overlap=0,
            language="english",
            length_function=self.count_tokens,
        )
        return text_spliter.split_text(text)

    def _download_and_cache_tokenizer(self):
        """
        Downloads and caches the tokenizer if it doesn't already exist locally.
        """
        tokenizer_dir = Path(self.config.ollama_local_tokenizer_dir)
        if tokenizer_dir.exists():
            self._logger.info(f"Tokenizer already cached in {tokenizer_dir}")
        else:
            self._logger.info(
                f"Downloading tokenizer for {self.config.ollama_model_id}…"
            )
            tokenizer = AutoTokenizer.from_pretrained(
                self.config.ollama_local_tokenizer_name, use_fast=True
            )
            tokenizer_dir.mkdir(parents=True, exist_ok=True)
            tokenizer.save_pretrained(tokenizer_dir)
            self._logger.info(f"Tokenizer saved in {tokenizer_dir}")

        return AutoTokenizer.from_pretrained(tokenizer_dir, use_fast=True)


if __name__ == "__main__":
    import ollama

    cmd = ollama.Client()
    models = cmd.list()
    for model in models.models:
        if "cloud" not in model.model and "x/" not in model.model:
            print(f"Deleting {model.model}")
            cmd.delete(model.model)
