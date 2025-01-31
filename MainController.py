import json
import os
from typing import Optional, Literal

import nltk
from langchain_text_splitters import NLTKTextSplitter
from tqdm import tqdm
from transformers import AutoTokenizer

from AudioGenerator import AudioGenerator
from OutputGenerator import OutputGenerator
from PDFHandler import PDFHandler
from TextProcessor import TextProcessor
from Translator import Translator


class MainController:

    def __init__(self, model_name: Literal["qwen2.5:32b", "mistral-small"], input_dir: str,
                 output_dir: Optional[str] = "translated",
                 source_language: Optional[str] = "English", target_language: Optional[str] = "Spanish",
                 token_size: int = 1000, only_translation: bool = False):
        """
        Initialize the MainController with configuration for translation and processing.

        :param model_name: The name of the model to use for processing.
        :param input_dir: Directory where input files are located.
        :param output_dir: Directory where output files will be saved (default: "translated").
        :param source_language: The source language of the text (default: "English").
        :param target_language: The target language for translation (default: "Spanish").
        :param token_size: The maximum number of tokens per processing block (default: 1000).
        :param only_translation: Flag to indicate if only translation should be performed (default: False).
        """

        # Download necessary NLTK resources
        nltk.download('punkt_tab')

        # Initialize instance variables
        self.only_translation = only_translation
        self.input_dir = input_dir
        self.source_language = source_language
        self.target_language = target_language

        # Initialize text splitters for source and target languages
        self.source_text_spliter = NLTKTextSplitter(chunk_size=token_size, chunk_overlap=0,
                                                    language=source_language.lower())
        self.target_text_spliter = NLTKTextSplitter(chunk_size=2000, chunk_overlap=0,
                                                    language=target_language.lower())

        # Set the output directory
        if output_dir == "translated":
            self.output_dir = os.path.join(input_dir, output_dir)
        else:
            self.output_dir = output_dir

        # Create output directory if it doesn't exist
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir, exist_ok=True)

        # Initialize handlers and processors
        self.pdf_handler = PDFHandler(input_dir)
        self.source_text_processor = TextProcessor(model_name=model_name)
        self.target_text_processor = TextProcessor(model_name=model_name)
        self.translator = Translator(source_language=source_language, target_language=target_language,
                                     model_name=model_name)
        self.output_generator = OutputGenerator()

    def get_progress_file(self, pdf_file: str) -> str:
        """
        Get the path for the progress file associated with the given PDF file.

        :param pdf_file: The path to the PDF file.
        :return: The path to the progress file.
        """
        # Get the base name of the PDF file (without extension)
        base_name = os.path.splitext(os.path.basename(pdf_file))[0]
        # Construct the path for the progress file
        progress_file = os.path.join(os.path.dirname(pdf_file), f"{base_name}.json")
        return progress_file

    def get_audiobook_file(self, pdf_file):
        """
        Generate the path for the audiobook file corresponding to a given PDF file.

        :param pdf_file: The path to the PDF file.
        :return: The path to the audiobook file in .m4a format.
        """
        # Extract the base name of the PDF file (without extension)
        base_name = os.path.splitext(os.path.basename(pdf_file))[0]
        # Construct the path for the audiobook file
        audio_file = os.path.join(self.output_dir, f"{base_name}.m4a")
        return audio_file

    def load_progress(self, progress_file):
        """
        Load the progress data from a given progress file.

        :param progress_file: The path to the progress file.
        :return: The loaded progress data as a dictionary, or an empty list if the file does not exist.
        """
        # Check if the progress file exists
        if os.path.exists(progress_file):
            # Open the file and load the JSON data
            with open(progress_file, "r") as file:
                return json.load(file)
        # Return an empty list if the file does not exist
        return []

    def save_progress(self, progress_file, data):
        """
        Save the given progress data to the specified progress file.

        :param progress_file: The path to the progress file.
        :param data: The progress data to save as a dictionary.
        """
        # Open the file and save the JSON data
        with open(progress_file, "w") as file:
            json.dump(data, file, indent=4)

    def process_pdfs(self):
        """
        Process all PDFs found in the input directory, extract content, translate text,
        and optionally reconstruct translated PDFs with corresponding audio files.
        """
        pdf_files = self.pdf_handler.find_pdfs()
        for pdf_file in tqdm(pdf_files, desc="Processing PDFs", unit="PDF"):
            print(f"Processing PDF: {pdf_file}")
            # Get or create progress metadata for the current PDF
            progress_file = self.get_progress_file(pdf_file)
            metadata = self.load_progress(progress_file)
            if len(metadata) == 0:
                metadata = self.pdf_handler.extract_content(pdf_file)
                self.save_progress(progress_file, metadata)

            translated_content = []

            # Iterate over the metadata to process each chunk
            for i in tqdm(range(len(metadata)), desc="Processing chunks", unit="Chunk", leave=False):
                md = metadata[i]
                if md["type"] == "text":
                    # Initialize translation variables
                    progress = self.get_progress(i, md, metadata, progress_file)
                    source_tokens = progress.get("tokenized_src", [])
                    translated_tokens = progress.get("tokenized_tgt", [])
                    corrected_tokens = progress.get("corrected_tokens", [])

                    # Process each token in the source text
                    for pos in tqdm(range(len(source_tokens)), desc="Processing tokens", unit="Token", leave=False):
                        source_tokens = self.analyze_source_grammar(i, md, metadata, pos, progress, progress_file, source_tokens)
                        translated_tokens = self.translate_chunk(i, md, metadata, pos, progress, progress_file, source_tokens, translated_tokens)
                        corrected_tokens = self.analyze_target_grammar(corrected_tokens, i, md, metadata, pos, progress, progress_file, translated_tokens)

                    # Combine corrected tokens and split into blocks
                    processed_blocks = "".join([t for t in corrected_tokens])
                    blocks = self.target_text_spliter.split_text(processed_blocks)

                    # Append each block to the translated content
                    for block in blocks:
                        translated_content.append({"text": block})

                if md["type"] == "image":
                    # Append image content to the translated content
                    for content in md["content"]:
                        translated_content.append({"images": content["images"][0]})

            if not self.only_translation:
                # Reconstruct the translated PDF and generate audio
                output_path = os.path.join(self.output_dir, f"translated_{os.path.basename(pdf_file)}")
                self.output_generator.reconstruct_pdf(pdf_file, translated_content, output_path)
                print(f"PDF traducido guardado en: {output_path}")

                # Generate audio from the translated content
                audio_generator = AudioGenerator(final_output=self.get_audiobook_file(pdf_file))
                audio_generator.process_texts(translated_content)

    def analyze_target_grammar(self, corrected_tokens, i, md, metadata, pos, progress, progress_file,
                               translated_tokens):
        """
        Analyze and correct the grammar of the translated tokens.

        :param corrected_tokens: List of tokens that have been corrected.
        :param i: Index of the current metadata item.
        :param md: Current metadata dictionary.
        :param metadata: List of all metadata dictionaries.
        :param pos: Current position in the token list.
        :param progress: Dictionary containing progress information.
        :param progress_file: Path to the progress file.
        :param translated_tokens: List of translated tokens.
        :return: Updated list of corrected tokens.
        """
        # Check if the current position has been corrected
        if len(corrected_tokens) < (pos + 1):
            # Correct the grammar of the current translated token
            corrected_text = self.target_text_processor.ollama_correct_text(
                text_block=translated_tokens[pos],
                source_language=self.target_language
            )
            corrected_tokens.append(corrected_text)

            # Update progress and metadata with the corrected tokens
            progress["corrected_tokens"] = corrected_tokens
            md["progress"] = progress
            metadata[i] = md

            # Save the updated progress to the progress file
            self.save_progress(progress_file, metadata)

        return corrected_tokens

    def translate_chunk(self, i, md, metadata, pos, progress, progress_file, source_tokens, translated_tokens):
        """
        Translate a single chunk of text from the source language to the target language.

        :param i: Index of the current metadata item.
        :param md: Current metadata dictionary.
        :param metadata: List of all metadata dictionaries.
        :param pos: Current position in the token list.
        :param progress: Dictionary containing progress information.
        :param progress_file: Path to the progress file.
        :param source_tokens: List of source tokens.
        :param translated_tokens: List of translated tokens.
        :return: Updated list of translated tokens.
        """
        # Check if the current position has been translated
        if len(translated_tokens) < (pos + 1):
            # Translate the current source token
            translated_text = self.translator.ollama_translate_text(source_tokens[pos]["text"])

            # Append the translated text to the list of translated tokens
            translated_tokens.append(translated_text)

            # Update progress and metadata with the translated tokens
            progress["tokenized_tgt"] = translated_tokens
            md["progress"] = progress
            metadata[i] = md

            # Save the updated progress to the progress file
            self.save_progress(progress_file, metadata)

        return translated_tokens

    def analyze_source_grammar(self, i, md, metadata, pos, progress, progress_file, source_tokens):
        """
        Analyze and correct the grammar of the source tokens.

        :param i: Index of the current metadata item.
        :param md: Current metadata dictionary.
        :param metadata: List of all metadata dictionaries.
        :param pos: Current position in the token list.
        :param progress: Dictionary containing progress information.
        :param progress_file: Path to the progress file.
        :param source_tokens: List of source tokens.
        :return: Updated list of source tokens with grammar corrected.
        """
        # Check if the current position has been analyzed
        if not source_tokens[pos]["analyzed"]:
            # Correct the grammar of the current source token
            source_tokens[pos]["text"] = self.source_text_processor.ollama_correct_text(
                text_block=source_tokens[pos]["text"],
                source_language=self.source_language
            )

            # Mark the token as analyzed
            source_tokens[pos]["analyzed"] = True

            # Update progress and metadata with the corrected tokens
            progress["tokenized_src"] = source_tokens
            md["progress"] = progress
            metadata[i] = md

            # Save the updated progress to the progress file
            self.save_progress(progress_file, metadata)

        return source_tokens

    def get_progress(self, pos, md, metadata, progress_file):
        """
        Get the progress of the current metadata item (i.e., the current page).

        :param pos: Index of the current metadata item.
        :param md: Current metadata dictionary.
        :param metadata: List of all metadata dictionaries.
        :param progress_file: Path to the progress file.
        :return: A dictionary containing the progress information.
        """
        # Get the progress dictionary
        progress = md.get("progress", {})

        # Check if the current page has been translated
        if not progress.get("translated", False):
            # Tokenize the source text
            tokenized = progress.get("tokenized_src", [])
            if len(tokenized) == 0:
                # Split the text into blocks
                tb_translated = "".join([t["text"] for t in md["content"]])
                # blocks = self.source_text_spliter.split_text(tb_translated)
                blocks = self.tiktoken_tokeize(tb_translated)
                # Create a list of tokens from the blocks
                progress["tokenized_src"] = [{"analyzed": False, "text": txt} for txt in blocks]
                # Update the progress dictionary
                md["progress"] = progress
                metadata[pos] = md
                # Clear the content of the current page
                md["content"] = []
                # Save the updated progress to the progress file
                self.save_progress(progress_file, metadata)

        return progress

    def tiktoken_tokeize(self, text):
        tokenizer = AutoTokenizer.from_pretrained("Qwen/Qwen2.5-32B")
        tokens = tokenizer.encode(text, add_special_tokens=False)

        print(f"Number of tokens: {len(tokens)}")
        return tokens
