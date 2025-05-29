import logging
import re
from typing import Optional, Tuple

from langchain_text_splitters import RecursiveCharacterTextSplitter

from LLM.GeminiAI import GeminiAI

# Configure logging
logger = logging.getLogger(__name__)


class TranslatorAgent:
    # --- Constants for clarity and maintainability ---
    _DEFAULT_MAX_TOKENS_PER_CALL = 8000
    _PROMPT_CHUNK_PLACEHOLDER = "[chunk]"  # Placeholder for estimating prompt size
    _MIN_CONTENT_TOKENS = 100  # Minimum tokens allowed for content after prompt
    _SHORT_TRANSLATION_THRESHOLD_FACTOR = 0.2  # Factor to detect potentially problematic short translations
    _EMPTY_CHUNK_MARKER_FORMAT = "[EMPTY_TRANSLATION_CHUNK_{index}]"
    _ERROR_CHUNK_MARKER_FORMAT = "[TRANSLATION_ERROR_CHUNK_{index}]"

    # The detailed prompt template. Kept within the method that uses it for locality,
    # as it's specific to the translation task and uses f-string formatting.
    # If it were static, it could be a class constant.
    # Given its length, ensure your IDE handles multi-line strings well for readability.

    def __init__(self, default_max_tokens_per_call: int = _DEFAULT_MAX_TOKENS_PER_CALL):
        """
        Initializes the TranslatorAgent.

        Args:
            default_max_tokens_per_call: The default maximum number of tokens
                                         for an LLM API call. This can be
                                         overridden in the translate_text method.
        """
        self.llm_client = GeminiAI()
        self.default_max_tokens_per_call = default_max_tokens_per_call

        # Splitter to divide text BEFORE translation if it exceeds the limit.
        # Its chunk_size will be dynamically adjusted in translate_text.
        self.pre_translation_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.default_max_tokens_per_call,  # Initial value, adjusted dynamically
            chunk_overlap=0,  # A larger overlap might help with context
            length_function=self.llm_client.count_tokens,
            separators=["\n\n", "\n", ". ", ", ", " ", ""],
        )

    def _get_translation_prompt_template(self, source_lang: str, target_lang: str) -> str:
        """
        Generates the detailed and optimized prompt template for the LLM.
        This prompt is crucial for guiding the LLM's translation process.
        """
        # THIS PROMPT IS CRUCIAL.
        # It's designed to guide the LLM through a multi-step process
        # of cleaning, translating, and refining literary text.
        prompt_template = f"""
You are a MASTER TRANSLATOR and meticulous LITERARY EDITOR. Your expertise spans diverse genres, including Japanese, Chinese, and Korean light novels, and Western fiction. You are tasked with translating and refining a text with utmost precision.

**Primary Objective:** Translate the provided text from {source_lang} to {target_lang} with exceptional accuracy, meticulously preserving its original style, tone, and authorial intent.

**Text for Processing:**
\"\"\"
{{text_chunk}}
\"\"\"

**Mandatory Processing Protocol (Follow these steps rigorously):**

1.  **Content Integrity Check & Source Text Pre-Correction ({source_lang}):**
    *   Thoroughly scan the entire text for any severe incoherence, corruption, or nonsensical segments. These often result from poor OCR or digital extraction.
    *   If such issues are identified, attempt to infer the correct meaning from the immediate surrounding context.
    *   Correct obvious typographical errors, misspellings, and punctuation mistakes in the {source_lang} text that clearly hinder comprehension or accurate translation.
    *   If sentences are incomplete due to extraction errors, try to complete them logically based on immediate context ONLY if the intended meaning is unequivocally clear. Otherwise, translate the fragment as-is, preserving its broken nature.
    *   **CRITICAL:** DO NOT invent new information, add content, or extensively rewrite the author's original style. If a small segment is truly untranslatable due to severe corruption and context does not clarify it, translate it as best as possible and you MAY indicate deep uncertainty within the translated text itself using bracketed, concise notes (e.g., "[corrupted text, best guess: ...]" or "[unclear phrase, literal translation: ...]"). Avoid this unless absolutely necessary.

2.  **Structural Cleaning (Pre-Translation - Applied to Source Text):**
    *   Identify and **COMPLETELY REMOVE** any extraneous text elements that are not part of the core narrative content. This primarily includes:
        *   Repetitive headers (e.g., book/chapter titles appearing on every page).
        *   Repetitive footers (e.g., page numbers, publisher notices, disclaimers repeated on pages).
        *   Stray page numbers or running heads embedded within the narrative flow.
    *   **DO NOT REMOVE:** Chapter numbers, actual chapter titles, or section headings that are integral parts of the story's structure and appear only once at the beginning of such sections.

3.  **High-Fidelity Translation ({source_lang} to {target_lang}):**
    *   Perform a precise, nuanced, and culturally sensitive translation into {target_lang}.
    *   **Style & Tone:** Meticulously replicate the author's original voice, narrative style (e.g., formal, informal, humorous, poetic), and emotional tone.
    *   **Idioms & Cultural Nuances:** Translate idioms, metaphors, and cultural references in a way that is natural and meaningful to a {target_lang} reader. If a direct equivalent is lacking, use a concise, contextually fitting adaptation or a very brief, unobtrusive explanation if essential for understanding. Avoid awkward or nonsensical literal translations.
    *   **Specialized Terminology (e.g., J/C/K literature):** For East Asian texts, handle honorifics (e.g., -san, -nim, gege, oppa), specific cultural terms, and unique concepts with consistency. Either retain them if they are commonly understood by the target audience or adapt them thoughtfully and consistently.
    *   **Proper Nouns:** Retain original character names, place names, and specific fictional terms unless a widely accepted, standard translation exists in {target_lang} (e.g., "London" to "Londres" if target is Spanish). Maintain consistency in their usage.

4.  **Post-Translation Refinement & Validation ({target_lang}):**
    *   Thoroughly review the translated text in {target_lang} for grammatical accuracy, correct spelling, and appropriate punctuation.
    *   Ensure all sentences are fluent, natural-sounding, and well-constructed in {target_lang}.
    *   **Paragraph Integrity:** Adjust paragraph breaks to ensure a natural, readable flow in {target_lang}. While generally respecting the source's paragraph delineations, prioritize coherence and readability in the target language. Remove superfluous line breaks that create choppy or fragmented text. Ensure paragraphs are well-formed.

5.  **Final Content Pruning (Post-Translation - Applied to Translated Text):**
    *   Review the translated text one last time and **REMOVE** any remaining non-narrative, structural, or paratextual sections that are not part of the story itself. This includes:
        *   Tables of contents, indices, glossaries.
        *   Copyright pages, dedications, acknowledgments (unless these are intrinsically part of the narrative or a foreword/afterword you are explicitly asked to translate).
        *   Bibliographies, reference lists.
        *   Original translator's notes or editor's notes (unless they provide critical context *for the story itself* and are not merely linguistic or publishing notes).
        *   Advertisements, publisher information, or promotional material.

6.  **Output Formatting (Strict Adherence Required):**
    *   You MUST return **ONLY** the fully translated, cleaned, and refined narrative text.
    *   **ABSOLUTELY NO** additional comments, greetings, preambles, apologies, self-reflections, or postscripts from you (the AI) should be included in the output.
    *   The output should be a single, continuous block of text, ready for direct use as the translated literary work.

Source Language: {source_lang}
Target Language: {target_lang}

**Final Translated and Polished Text:**
"""
        return prompt_template

    def _setup_text_splitting_parameters(
            self, source_lang: str, target_lang: str, effective_max_tokens_per_call: int
    ) -> int:
        """
        Calculates token limits for text chunks and adjusts the pre-translation splitter.

        Returns:
            The maximum number of tokens allowed for content in each chunk.
        """
        base_prompt_template = self._get_translation_prompt_template(source_lang, target_lang)
        # Estimate prompt size using a placeholder for the actual text chunk
        prompt_base_tokens = self.llm_client.count_tokens(
            base_prompt_template.format(text_chunk=self._PROMPT_CHUNK_PLACEHOLDER)
        )

        max_content_tokens = effective_max_tokens_per_call - prompt_base_tokens
        # Ensure max_content_tokens is not negative or too small
        max_content_tokens = max(self._MIN_CONTENT_TOKENS, max_content_tokens)

        logger.info(f"  - Base Prompt Tokens (estimated): {prompt_base_tokens}")
        logger.info(f"  - Max Content Tokens per Chunk: {max_content_tokens}")
        logger.info(f"  - Total Limit per API Call (effective): {effective_max_tokens_per_call}")

        # Adjust the splitter's chunk size dynamically.
        # Note: Accessing _chunk_size directly is a workaround if no public setter exists.
        self.pre_translation_splitter._chunk_size = max_content_tokens
        return max_content_tokens

    def _translate_single_chunk(
            self,
            chunk: str,
            chunk_index: int,
            total_chunks: int,
            max_content_tokens: int,
            base_prompt_template_with_chunk_placeholder: str
    ) -> str:
        """
        Translates a single chunk of text using the LLM.

        Args:
            chunk: The text chunk to translate.
            chunk_index: The 0-based index of the current chunk.
            total_chunks: The total number of chunks.
            max_content_tokens: The maximum token limit for this chunk's content.
            base_prompt_template_with_chunk_placeholder: The prompt template with
                                                         source/target languages filled,
                                                         still containing '{text_chunk}'.
        Returns:
            The translated chunk, or a marker string if an error occurred or
            the translation was empty.
        """
        current_chunk_tokens = self.llm_client.count_tokens(chunk)
        logger.info(
            f"  - Translating chunk {chunk_index + 1}/{total_chunks} ({current_chunk_tokens} tokens)..."
        )

        if current_chunk_tokens > max_content_tokens:
            logger.warning(
                f"  - Warning: Chunk {chunk_index + 1} ({current_chunk_tokens} tokens) "
                f"exceeds the calculated content limit ({max_content_tokens} tokens). "
                "This may cause errors. Attempting anyway."
            )

        prompt = base_prompt_template_with_chunk_placeholder.format(text_chunk=chunk)

        try:
            translated_chunk = self.llm_client.call_model(prompt)

            # Validate the response: check for empty or unusually short translations
            if not translated_chunk or \
                    len(translated_chunk) < len(chunk) * self._SHORT_TRANSLATION_THRESHOLD_FACTOR:
                logger.warning(
                    f"  - Warning: Possible issue with the translation of chunk {chunk_index + 1}. "
                    "Response empty or very short."
                )
                if not translated_chunk:  # Handles None or empty string from LLM
                    return self._EMPTY_CHUNK_MARKER_FORMAT.format(index=chunk_index + 1)

            # Ensure a string is returned, even if call_model hypothetically returned None
            # and it wasn't caught by the 'if not translated_chunk' above.
            return translated_chunk if translated_chunk is not None else ""

        except Exception as e:
            logger.error(f"Error during LLM call for chunk {chunk_index + 1}: {e}")
            return self._ERROR_CHUNK_MARKER_FORMAT.format(index=chunk_index + 1)

    def translate_text(self, full_text: str, source_lang: str, target_lang: str,
                       max_tokens_per_call_override: Optional[int] = None) -> str:
        """
        Splits, translates, and joins the text using the LLM via the GeminiAI client.

        Args:
            full_text: The entire text to be translated.
            source_lang: The source language of the text.
            target_lang: The target language for translation.
            max_tokens_per_call_override: Optionally override the default max tokens
                                          for LLM API calls for this specific translation.

        Returns:
            The full translated text as a single string. Returns an empty string
            if the input text results in no processable chunks. May contain
            error markers for failed chunks.
        """
        logger.info(f"Starting translation from {source_lang} to {target_lang}...")

        effective_max_tokens = (
            max_tokens_per_call_override
            if max_tokens_per_call_override is not None
            else self.default_max_tokens_per_call
        )

        max_content_tokens = self._setup_text_splitting_parameters(
            source_lang, target_lang, effective_max_tokens
        )

        original_chunks = self.pre_translation_splitter.split_text(full_text)
        logger.info(
            f"  - Original text split into {len(original_chunks)} chunks for translation "
            f"(target content token size: {max_content_tokens})."
        )

        if not original_chunks:
            logger.warning("  - Warning: The original text resulted in 0 chunks after splitting. Check the input text.")
            return ""

        translated_text_parts = []
        total_chunks = len(original_chunks)

        # Get the base prompt template once, with {text_chunk} as a placeholder
        # This template already has source_lang and target_lang filled in.
        prompt_template_for_chunks = self._get_translation_prompt_template(source_lang, target_lang)

        for i, chunk in enumerate(original_chunks):
            translated_chunk_content = self._translate_single_chunk(
                chunk,
                chunk_index=i,
                total_chunks=total_chunks,
                max_content_tokens=max_content_tokens,
                base_prompt_template_with_chunk_placeholder=prompt_template_for_chunks
            )
            translated_text_parts.append(translated_chunk_content)

        logger.info("Translation of all chunks completed.")

        # Join the translated chunks.
        full_translated_text = "\n\n".join(translated_text_parts)

        # Final cleanup: reduce multiple newlines to a maximum of two, and strip whitespace.
        full_translated_text = re.sub(r'\n{3,}', '\n\n', full_translated_text).strip()

        return full_translated_text
