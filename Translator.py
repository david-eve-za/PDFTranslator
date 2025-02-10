# Clase Translator
import subprocess
from typing import Optional

from ollama import ChatResponse, chat, generate, show, ResponseError, pull, create


class Translator:
    LANGUAGES = {
        "Inglés": "en",
        "Español": "es",
        "Francés": "fr",
        "Alemán": "de",
        "Italiano": "it"
    }

    def __init__(
            self,
            source_language: str,
            target_language: str,
            model_name: Optional[str] = "qwen2.5:32b"
    ) -> None:
        self.source_language = source_language
        self.target_language = target_language
        self._base_model_name = model_name
        self._init_model()

    def _init_model(self):
        try:
            show(self._get_custom_model_name())
        except ResponseError:
            self._create_custom_model()

    def _create_custom_model(self):
        pull(self._base_model_name)
        modelfile = (
            f"FROM {self._base_model_name}\n"
            f"PARAMETER temperature 0.1\n"
            f"PARAMETER top_p 0.90\n" # Enfoque en distribuciones probabilísticas clave
            f"PARAMETER top_k 50\n" # Muestra de vocabulario relevante
            f"PARAMETER repeat_penalty 1.2\n" # Penalización de repetición
            f"PARAMETER mirostat 2\n" # Control de calidad lexical avanzado
            f"PARAMETER num_ctx 8192\n"
            f"SYSTEM {self.get_prompt()}\n"
            "USER {{user_text}}\n"
            "ASSISTANT {{assistant_text}}"
            "".strip()
        )
        create()

    def _get_custom_model_name(self):
        return f"{self._base_model_name}_tranlator_{self.LANGUAGES[self.source_language]}_{self.LANGUAGES[self.target_language]}"

    def get_prompt(self, user_text: str = "") -> str:
        template = (
            f"Hi! I need your help translating a light novel/web novel from {self.source_language} to {self.target_language}. Here’s how I’d like you to approach it:\n"
            "1. Accuracy and Tone:\n"
            f"   Keep the original style (e.g., funny, serious, or dramatic) and adapt any idioms or wordplay creatively into {self.target_language} so it feels natural.\n"
            "   Make sure the characters’ voices stay consistent in dialogues (e.g., if someone speaks formally or uses slang, keep that vibe).\n"
            "2. Cultural Context:\n"
            "   If there are specific Japanese/Chinese/Korean cultural references (like honorifics -san/-sama or festivals), could you explain them briefly in [brackets] for clarity?\n"
            f"   For measurements (feet → meters) or currencies, adapt them to make sense for {self.target_language} readers, but leave proper nouns (like magic skills or fantasy terms) as they are.\n"
            "3. Terminology Consistency:\n"
            f"   Use terms that are already familiar to {self.target_language}-speaking fans for common genres (like isekai, system, or cultivation). If there’s no clear equivalent, just leave it in {self.source_language} with a note.\n"
            "   Keep character names, locations, and skills consistent throughout (e.g., if Shadow Monarch is commonly translated as Monarca de las Sombras, stick to that).\n"
            "4. Format and Fluency:\n"
            "   Keep line breaks, onomatopoeia (like whoosh → ¡swoosh!), and emphasis (italics or bold) as they are in the original.\n"
            f"   Make sure the text flows naturally in {self.target_language}, avoiding literal translations that might sound awkward.\n"
            "5. Additional Notes:\n"
            "   If you come across any ambiguous or culturally tricky parts, just flag them with [¿?] so I can take a closer look.\n"
            "Provide the translated text only formated as html.\n"
            f"Here’s the text I’d like you to translate:\n{user_text}"
        )
        return template

    def ollama_translate_text(self, text: str) -> str:
        # template = (
        #     "You are translating a document. Maintain the context of the previous text.\n"
        #     f"Translate the following text from {self.source_language} to {self.target_language}:\n"
        #     # f"text: {text}\n\n"
        #     "Provide the translated text only."
        # )
        # input = [{
        #     "role": "system",
        #     "content": template
        # }, {
        #     "role": "user",
        #     "content": text
        # }]
        # response: ChatResponse = chat(model=self.model_name, messages=input, options={"temperature": 0.2},
        #                               keep_alive=15)
        # return response["message"]["content"]
        # stdout, stderr = self.run_ollama_command(template)
        # if stdout:
        #     print("Salida estándar:")
        #     print(stdout)
        #
        # if stderr:
        #     print("Salida de error:")
        #     print(stderr)
        response = generate(model=self._base_model_name, prompt=self.get_prompt(text),
                            options={"temperature": 0.1, "num_ctx": 8000})
        return response["response"]

    def run_ollama_command(self, text: str) -> tuple[str, str] | tuple[None, str]:
        try:
            result = subprocess.run(
                ["ollama", "run", self._base_model_name, text],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                shell=False
            )
            return result.stdout, result.stderr
        except Exception as e:
            return None, f"Error running ollama command: {e}"
