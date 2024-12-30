import json
import os
from typing import Optional, Literal

import nltk
from langchain_text_splitters import NLTKTextSplitter

from OutputGenerator import OutputGenerator
from PDFHandler import PDFHandler
from TextProcessor import TextProcessor
from Translator import Translator


class MainController:
    PROGRESS_FILE = "translation_progress.json"

    def __init__(self, model_name: Literal["qwen2.5:32b", "mistral-small"], input_dir: str,
                 output_dir: Optional[str] = "translated",
                 source_language: Optional[str] = "English", target_language: Optional[str] = "Spanish",
                 token_size: int = 1000):
        nltk.download('punkt_tab')
        self.input_dir = input_dir
        self.source_language = source_language
        self.target_language = target_language
        self.source_text_spliter = NLTKTextSplitter(chunk_size=token_size, chunk_overlap=0,
                                                    language=source_language.lower())
        self.target_text_spliter = NLTKTextSplitter(chunk_size=750, chunk_overlap=0,
                                                    language=target_language.lower())
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

    def get_progress_file(self, pdf_file):
        # Take entire Path of pdf_file as input and return the path of the progress file as output with extension .json
        base_name = os.path.splitext(os.path.basename(pdf_file))[0]
        progress_file = os.path.join(os.path.dirname(pdf_file), f"{base_name}.json")
        return progress_file

    def load_progress(self, progress_file):
        """
        Carga el estado de progreso desde un archivo JSON, si existe.
        """
        if os.path.exists(progress_file):
            with open(progress_file, "r") as file:
                return json.load(file)
        return []

    def save_progress(self, progress_file, data):
        """
        Guarda el estado de progreso actual en un archivo JSON.
        """
        with open(progress_file, "w") as file:
            json.dump(data, file, indent=4)

    def process_pdfs(self):

        pdf_files = self.pdf_handler.find_pdfs()
        for pdf_file in pdf_files:
            progress_file = self.get_progress_file(pdf_file)
            metadata = self.load_progress(progress_file)
            if len(metadata) == 0:
                metadata = self.pdf_handler.extract_content(pdf_file)
                self.save_progress(progress_file, metadata)
            translated_content = []
            for i in range(len(metadata)):  # Iterate over the metadata:
                md = metadata[i]
                if md["type"] == "text":
                    tb_translated = ""
                    progress = md.get("progress", {})
                    if not progress.get("translated", False):
                        tokenized = progress.get("tokenized_eng", [])
                        if len(tokenized) == 0:
                            tb_translated = "".join([t["text"] for t in md["content"]])
                            blocks = self.source_text_spliter.split_text(tb_translated)
                            md["tokenized_eng"] = [{"analyzed": False, "text": txt} for txt in blocks]
                            metadata[i] = md
                            self.save_progress(progress_file, metadata)
                    processed_blocks = ""
                    for block in blocks:
                        corrected_text = self.source_text_processor.correct_text(text_block=block,
                                                                                 source_language=self.source_language)
                        translated_text = self.translator.translate_text(corrected_text)
                        corrected_text = self.target_text_processor.correct_text(text_block=translated_text,
                                                                                 source_language=self.target_language)
                        processed_blocks += corrected_text
                    blocks = self.target_text_spliter.split_text(processed_blocks)
                    for block in blocks:
                        translated_content.append({"text": block})
                if md["type"] == "image":
                    for content in md["content"]:
                        translated_content.append({"images": content["images"]})
            output_path = os.path.join(
                self.output_dir,
                f"translated_{os.path.basename(pdf_file)}",
            )
            self.output_generator.reconstruct_pdf(content, translated_content, output_path)
            print(f"PDF traducido guardado en: {output_path}")
