# Clase Translator
import subprocess
from typing import Optional

from ollama import ChatResponse, chat, generate


class Translator:
    def __init__(
            self,
            source_language: str,
            target_language: str,
            model_name: Optional[str] = "qwen2.5:32b"
    ) -> None:
        self.source_language = source_language
        self.target_language = target_language
        self.model_name = model_name

    def ollama_translate_text(self, text: str) -> str:
        template = (
            "You are translating a document. Maintain the context of the previous text.\n"
            f"Translate the following text from {self.source_language} to {self.target_language}:\n"
            # f"text: {text}\n\n"
            "Provide the translated text only."
        )
        input = [{
            "role": "system",
            "content": template
        }, {
            "role": "user",
            "content": text
        }]
        response: ChatResponse = chat(model=self.model_name, messages=input, options={"temperature": 0.2},
                                      keep_alive=15)
        return response["message"]["content"]
        # stdout, stderr = self.run_ollama_command(template)
        # if stdout:
        #     print("Salida estándar:")
        #     print(stdout)
        #
        # if stderr:
        #     print("Salida de error:")
        #     print(stderr)
        # response = generate(model=self.model_name,prompt=template,options={"temperature": 0.2})
        # return response["response"]

    def run_ollama_command(self, text: str) -> tuple[str, str] | tuple[None, str]:
        try:
            result = subprocess.run(
                ["ollama", "run", self.model_name, text],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                shell=False
            )
            return result.stdout, result.stderr
        except Exception as e:
            return None, f"Error running ollama command: {e}"
