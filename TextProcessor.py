# Clase TextProcessor
from difflib import unified_diff
from typing import Optional

from langchain.chains.llm import LLMChain
from langchain.memory import ConversationBufferWindowMemory
from langchain.prompts import PromptTemplate
from langchain_ollama import OllamaLLM


class TextProcessor:
    def __init__(self, model_name: Optional[str] = "qwen2.5:32b"):
        """
        Initialize the TextProcessor class.

        Parameters:
            model_name (str): The name of the model to use for processing (default: "qwen2.5:32b").
        """

        # Initialize the memory and prompt for the LLM chain
        self.memory = ConversationBufferWindowMemory(
            memory_key="context",
            input_key="text",
            k=1  # Only remember the current text block
        )
        self.prompt = PromptTemplate(
            input_variables=["text", "source_language"],
            template=(
                "Act as an editor who carefully analyzes a document in {source_language} language.\n\n"
                "Understand the text context, identify potential errors, and make only necessary corrections\n\n"
                "to improve readability and coherence without altering the original tone or structure:\n\n {text}\n\n"
                "Provide the corrected text only without context or any other information."
            ),
        )
        # Initialize the LLM chain
        self.llm_chain = LLMChain(
            llm=OllamaLLM(model=model_name, temperature=0.1),
            prompt=self.prompt,
            memory=self.memory,
            verbose=False  # Don't print out the LLM chain output
        )

    def correct_text(self, text_block, source_language: str) -> str:
        """
        Correct the grammar and improve the readability of the given text block.

        Parameters:
            text_block (str): The text to be corrected.
            source_language (str): The language of the input text.

        Returns:
            str: The corrected text with improved grammar and readability.
        """
        # Prepare input for the LLM chain
        input = {
            "text": text_block,
            "source_language": source_language
        }

        # Invoke the LLM chain to process and correct the text
        output = self.llm_chain.invoke(input)

        # Extract the corrected text from the output
        corrected_text = output["text"]

        return corrected_text
