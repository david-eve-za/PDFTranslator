# Clase MainController
import os
from typing import Optional, Literal

from OutputGenerator import OutputGenerator
from PDFHandler import PDFHandler
from TextProcessor import TextProcessor
from Translator import Translator


class MainController:
    def __init__(self, model_name: Literal["qwen2.5:32b", "mistral-small"], input_dir: str,
                 output_dir: Optional[str] = "translated",
                 source_language: Optional[str] = "English", target_language: Optional[str] = "Spanish"):
        self.input_dir = input_dir
        self.source_language = source_language
        self.target_language = target_language
        if output_dir == "translated":
            self.output_dir = os.path.join(input_dir, output_dir)
        else:
            self.output_dir = output_dir
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir, exist_ok=True)
        self.pdf_handler = PDFHandler(input_dir)
        self.source_text_processor = TextProcessor(model_name=model_name)
        self.target_text_processor = TextProcessor(model_name=model_name)
        self.translator = Translator(source_language=source_language, target_language=target_language,
                                     memory_window_size=1, model_name=model_name)
        self.output_generator = OutputGenerator()

    def process_pdfs(self):
        """Coordina el flujo completo de procesamiento de PDFs."""
        pdf_files = self.pdf_handler.find_pdfs()
        for pdf_file in pdf_files:
            content = self.pdf_handler.extract_content(pdf_file)
            translated_content = []
            for page in content:
                if page["text"]:
                    # Split text in chunks for almost 60000 tokens
                    blocks = self.split_text_in_chunks(page["text"], 60000)
                    processed_blocks = []
                    for block in blocks:
                        corrected_text = self.source_text_processor.correct_text(text_block=block, source_language=self.source_language)
                        translated_text = self.translator.translate_text(corrected_text)
                        corrected_text = self.target_text_processor.correct_text(text_block=translated_text, source_language=self.target_language)
                        processed_blocks.append(corrected_text)
                    translated_content.append({"text": "\n".join(processed_blocks)})
                if page["images"]:
                    # translated_content[-1]["images"] = page["images"]
                    translated_content.append({"images": page["images"]})
            output_path = os.path.join(
                self.output_dir,
                f"translated_{os.path.basename(pdf_file)}",
            )
            self.output_generator.reconstruct_pdf(content, translated_content, output_path)
            print(f"PDF traducido guardado en: {output_path}")

    @staticmethod
    def split_text_in_chunks(text: str, max_tokens: int = 60000):
        """Divide el texto en bloques que no superen el n mero de tokens m ximo."""
        blocks = []
        current_block = ""
        current_tokens = 0
        for line in text.splitlines(keepends=True):
            for sentence in line.split("."):
                if current_tokens + len(sentence.split()) > max_tokens:
                    blocks.append(current_block)
                    current_block = sentence
                    current_tokens = len(sentence.split())
                else:
                    current_block += sentence
                    current_tokens += len(sentence.split())
        blocks.append(current_block)
        return blocks
