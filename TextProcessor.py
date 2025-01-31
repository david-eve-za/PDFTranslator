# Clase TextProcessor
from typing import Optional

from ollama import ChatResponse, chat


class TextProcessor:
    def __init__(self, model_name: Optional[str] = "qwen2.5:32b"):
        self.model_name = model_name

    def ollama_correct_text(self, text_block: str, source_language: str) -> str:
        template = (
            f"Act as an editor who carefully analyzes a document in {source_language} language.\n"
            "Understand the text context, identify potential errors, and make only necessary corrections\n"
            f"to improve readability and coherence without altering the original tone or structure:\n"
            "Provide the corrected text only without context or any other information."
        )
        input = [{
            "role": "system",
            "content": template
        }, {
            "role": "user",
            "content": text_block
        }]
        response: ChatResponse = chat(model=self.model_name, messages=input, options={"temperature": 0.1})
        return response["message"]["content"]
