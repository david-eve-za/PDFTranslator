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
