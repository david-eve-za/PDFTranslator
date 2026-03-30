from abc import ABC, abstractmethod
from enum import Enum
from typing import List


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


class BaseLLM(ABC):
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
    def split_into_limit(
        self, text: str, language: BCP47Language = BCP47Language.ENGLISH
    ) -> List[str]:
        pass
