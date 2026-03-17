from abc import ABC, abstractmethod
from typing import List


class LLMService(ABC):
    @abstractmethod
    def call_model(self, prompt: str) -> str:
        pass

    @abstractmethod
    def get_current_model_name(self) -> str:
        pass

    @abstractmethod
    def count_tokens(self, text: str) -> int:
        pass

    @abstractmethod
    def split_into_limit(self, text: str) -> List[str]:
        pass
