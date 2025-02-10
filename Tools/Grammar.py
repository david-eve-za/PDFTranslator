from huggingface_hub import login
from supabase import create_client, Client
from sympy import false
from together import Together
import os

from transformers import AutoTokenizer

from LLM.APIClient import APIClient
from MongoDB import MongoDBManager
from Tools.SupabaseWraper import SupabaseManager

SUPABASE_URL: str = os.getenv("SUPABASE_URL", "http://localhost:8000/")
SUPABASE_KEY: str = os.getenv("SUPABASE_KEY",
                                  "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.ewogICJyb2xlIjogInNlcnZpY2Vfcm9sZSIsCiAgImlzcyI6ICJzdXBhYmFzZSIsCiAgImlhdCI6IDE3NDIxODc2MDAsCiAgImV4cCI6IDE4OTk5NTQwMDAKfQ.qwjlgmU_2rQj3H7KeillHV49WjuVQzMf5Qr-Up20E0g")
manager = SupabaseManager(SUPABASE_URL, SUPABASE_KEY)


class InvisibleTextCorrector(APIClient):
    def __init__(self):
        APIClient.__init__(self=self, tokens_per_minute=131072, calls_per_minute=60, daily_calls=200000)
        self._client = Together(
            api_key=os.getenv("TOGETHER_API_KEY"))
        login(token=os.getenv("HF_TOKEN"))
        self._text_generation_model = "meta-llama/Llama-3.3-70B-Instruct-Turbo-Free"
        self.tokenizer = AutoTokenizer.from_pretrained("meta-llama/Llama-3.3-70B-Instruct")

        # Prompt fiel al original en inglés
        self.correction_prompt = """<|im_start|>system
You are a professional text corrector for all languages. Analyze and silently fix:
- Grammar/syntax errors
- Punctuation mistakes
- Typos and encoding errors
- Incomplete sentences
Preserve original formatting, style, and structure.
Never add explanations or markings.
Only return the corrected text.<|im_end|>
<|im_start|>user
{text}<|im_end|>
<|im_start|>assistant
"""

    def _count_tokens(self, text):
        return len(self.tokenizer.encode(text, add_special_tokens=False))

    def stealth_correct(self, text):
        full_prompt = self.correction_prompt.format(text=text)
        num_tokens = self._count_tokens(full_prompt)
        self.wait_if_needed(num_tokens)

        try:
            response = self._client.completions.create(
                model=self._text_generation_model,
                prompt=full_prompt,
                temperature=0.0,  # Máxima precisión
                max_tokens=4000,
                stop=["<|im_end|>", "</correction>"],
                echo=False
            )

            corrected_text = response.choices[0].text.strip()
            # Limpieza final de posibles artefactos
            return corrected_text.replace("</correction>", "").strip()

        except Exception as e:
            print(f"API Error: {str(e)}")
            return None


# Ejemplo de uso
if __name__ == "__main__":

    corrector = InvisibleTextCorrector()

    books = manager.get_grouped_books()

    books = [b for b in books if "Campione" in b["file_path"]]
    for book in books:
        for p_id in sorted(book["record_ids"]):
            pages = manager.get_pages(query={"book_id":p_id,"content_type":"text","corrected":False})
            pages.sort(key=lambda x: x["page_number"])
            for page in pages:
                token_size = len(corrector.tokenizer.encode(page["content"],add_special_tokens=False))
                corrected_text = corrector.stealth_correct(page["content"])
                manager.update_page(page_id=page["id"],update_data={"content_corrected":corrected_text,"corrected":True})
