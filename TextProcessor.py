# Clase TextProcessor
from difflib import unified_diff
from typing import Optional

from langchain.chains.llm import LLMChain
from langchain.memory import ConversationBufferWindowMemory
from langchain.prompts import PromptTemplate
from langchain_ollama import OllamaLLM


class TextProcessor:
    def __init__(self, model_name: Optional[str] = "qwen2.5:32b"):
        # Configure LangChain with contextual memory
        self.memory = ConversationBufferWindowMemory(
            memory_key="context",
            input_key="text",
            k=1
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
        self.llm_chain = LLMChain(
            llm=OllamaLLM(model=model_name, temperature=0.1),
            prompt=self.prompt,
            memory=self.memory,
            verbose=False
        )

    def correct_text(self, text_block, source_language: str):
        """Corrige errores ortográficos, gramaticales y mejora la coherencia."""
        input = {
            "text": text_block,
            "source_language": source_language
        }

        # Run the LLM chain to generate the translation
        output = self.llm_chain.invoke(input)

        # Extract the translated text from the output
        corrected_text = output["text"]

        # Mostrar diferencias entre el texto original y el corregido
        # if corrected_text.strip() != text_block.strip():
        #     print("\n--- Corrections Made ---")
        #     for diff in unified_diff(text_block.splitlines(), corrected_text.splitlines(), lineterm='',
        #                              fromfile='Original', tofile='Corrected'):
        #         print(diff)
        # else:
        #     print("\n--- No Corrections Made ---")

        return corrected_text
