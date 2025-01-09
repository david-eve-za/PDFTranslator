import json
import os
from typing import Optional, Literal

import nltk
from langchain_text_splitters import NLTKTextSplitter
from tqdm import tqdm

from AudioGenerator import AudioGenerator
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
        self.target_text_spliter = NLTKTextSplitter(chunk_size=1500, chunk_overlap=0,
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

    def get_audiobook_file(self, pdf_file):
        base_name = os.path.splitext(os.path.basename(pdf_file))[0]
        audio_file = os.path.join(self.output_dir, f"{base_name}.m4a")
        return audio_file

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
        for pdf_file in tqdm(pdf_files, desc="Processing PDFs", unit="PDF"):
            progress_file = self.get_progress_file(pdf_file)
            metadata = self.load_progress(progress_file)
            if len(metadata) == 0:
                metadata = self.pdf_handler.extract_content(pdf_file)
                self.save_progress(progress_file, metadata)
            translated_content = []
            for i in tqdm(range(len(metadata)), desc="Processing chunks", unit="Chunk",
                          leave=False):  # Iterate over the metadata:
                md = metadata[i]
                if md["type"] == "text":
                    tb_translated = ""
                    progress = self.get_progress(i, md, metadata, progress_file)
                    source_tokens = progress.get("tokenized_src", [])
                    translated_tokens = progress.get("tokenized_tgt", [])
                    corrected_tokens = progress.get("corrected_tokens", [])
                    for pos in tqdm(range(len(source_tokens)), desc="Processing tokens", unit="Token", leave=False):
                        source_tokens = self.analyze_source_grammar(i, md, metadata, pos, progress, progress_file,
                                                                    source_tokens)
                        translated_tokens = self.translate_chunk(i, md, metadata, pos, progress, progress_file,
                                                                 source_tokens,
                                                                 translated_tokens)
                        corrected_tokens = self.analyze_target_grammar(corrected_tokens, i, md, metadata, pos, progress,
                                                                       progress_file,
                                                                       translated_tokens)

                    processed_blocks = "".join([t for t in corrected_tokens])
                    blocks = self.target_text_spliter.split_text(processed_blocks)
                    for block in blocks:
                        translated_content.append({"text": block})
                if md["type"] == "image":
                    for content in md["content"]:
                        translated_content.append({"images": content["images"][0]})
            output_path = os.path.join(
                self.output_dir,
                f"translated_{os.path.basename(pdf_file)}",
            )
            self.output_generator.reconstruct_pdf(pdf_file, translated_content, output_path)
            print(f"PDF traducido guardado en: {output_path}")
            audio_generator = AudioGenerator(final_output=self.get_audiobook_file(pdf_file))
            audio_generator.process_texts(translated_content)

    def analyze_target_grammar(self, corrected_tokens, i, md, metadata, pos, progress, progress_file,
                               translated_tokens):
        if len(corrected_tokens) < (pos + 1):
            corrected_tokens.append(
                self.target_text_processor.correct_text(text_block=translated_tokens[pos],
                                                        source_language=self.target_language))
            progress["corrected_tokens"] = corrected_tokens
            md["progress"] = progress
            metadata[i] = md
            self.save_progress(progress_file, metadata)
        return corrected_tokens

    def translate_chunk(self, i, md, metadata, pos, progress, progress_file, source_tokens, translated_tokens):
        if len(translated_tokens) < (pos + 1):
            translated_tokens.append(self.translator.translate_text(source_tokens[pos]["text"]))
            progress["tokenized_tgt"] = translated_tokens
            md["progress"] = progress
            metadata[i] = md
            self.save_progress(progress_file, metadata)
        return translated_tokens

    def analyze_source_grammar(self, i, md, metadata, pos, progress, progress_file, source_tokens):
        if not source_tokens[pos]["analyzed"]:
            source_tokens[pos]["analyzed"] = True
            source_tokens[pos]["text"] = self.source_text_processor.correct_text(
                text_block=source_tokens[pos]["text"],
                source_language=self.source_language)
            progress["tokenized_src"] = source_tokens
            md["progress"] = progress
            metadata[i] = md
            self.save_progress(progress_file, metadata)
        return source_tokens

    def get_progress(self, pos, md, metadata, progress_file):
        progress = md.get("progress", {})
        if not progress.get("translated", False):
            tokenized = progress.get("tokenized_src", [])
            if len(tokenized) == 0:
                tb_translated = "".join([t["text"] for t in md["content"]])
                blocks = self.source_text_spliter.split_text(tb_translated)
                progress["tokenized_src"] = [{"analyzed": False, "text": txt} for txt in blocks]
                md["progress"] = progress
                metadata[pos] = md
                md["content"] = []
                self.save_progress(progress_file, metadata)
        return progress
