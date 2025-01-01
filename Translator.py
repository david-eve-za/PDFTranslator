# Clase Translator
from typing import Optional

from langchain.chains.llm import LLMChain
from langchain.memory import ConversationBufferWindowMemory
from langchain.prompts import PromptTemplate
from langchain_ollama import OllamaLLM


class Translator:
    def __init__(
        self,
        source_language: str,
        target_language: str,
        model_name: Optional[str] = "qwen2.5:32b",
        memory_window_size: int = 5
    ) -> None:
        """
        Initialize the translation system with the source language, target language, and language model.

        :param source_language: The original language of the text (e.g., 'English').
        :param target_language: The language to translate the text to (e.g., 'Spanish').
        :param model_name: The name of the language model (default: 'gemma2:27b').
        :param memory_window_size: The number of previous interactions to remember in the conversation history.
        """
        self.source_language = source_language
        self.target_language = target_language

        # Check that the specified memory window size is valid
        if memory_window_size < 1:
            raise ValueError(f"Invalid memory window size: {memory_window_size}")

        # Configure LangChain with contextual memory
        self.memory = ConversationBufferWindowMemory(
            memory_key="context",
            input_key="text",
            k=memory_window_size
        )
        self.prompt = PromptTemplate(
            input_variables=["text", "source_language", "target_language"],
            template=(
                "You are translating a document. Maintain the context of the previous text.\n\n"
                "Translate the following text from {source_language} to {target_language}:\n\n"
                "{text}\n\n"
                "Provide the translated text only."
            ),
        )
        self.llm_chain = LLMChain(
            llm=OllamaLLM(model=model_name, temperature=0.1),
            prompt=self.prompt,
            memory=self.memory,
            verbose=False
        )

    def translate_text(self, text: str) -> str:
        """
        Translate the given text from the source language to the target language.

        :param text: The text to translate.
        :return: The translated text.
        """
        # Check that the text is not empty
        if not text.strip():
            return ""

        # Create a new input for the LLM chain
        input = {
            "text": text,
            "source_language": self.source_language,
            "target_language": self.target_language
        }

        # Run the LLM chain to generate the translation
        output = self.llm_chain.invoke(input)

        # Extract the translated text from the output
        translated_text = output["text"]

        return translated_text