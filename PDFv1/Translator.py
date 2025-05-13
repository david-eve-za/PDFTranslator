import logging
import re
from typing import Optional

from langchain_text_splitters import RecursiveCharacterTextSplitter

from LLM.GeminiAI import GeminiAI

# Configure logging
logger = logging.getLogger(__name__)


class TranslatorAgent:
    # Modified to accept a GeminiAI instance
    def __init__(self, MAX_TOKENS_PER_CALL=8000):
        self.llm_client = GeminiAI()  # Stores the LLM client instance

        # Splitter to divide text BEFORE translation if it exceeds the limit
        # Will use the count_tokens function of the provided LLM client
        self.pre_translation_splitter = RecursiveCharacterTextSplitter(
            # The chunk size should be less than the API's total limit,
            # considering the system prompt and the base user prompt.
            # We will calculate this dynamically in translate_text.
            chunk_size=MAX_TOKENS_PER_CALL,  # Initial value, will be adjusted
            chunk_overlap=0,  # A larger overlap might help with context between chunks
            length_function=self.llm_client.count_tokens,  # Uses the Gemini client's token counter
            separators=["\n\n", "\n", ". ", ", ", " ", ""]  # Common separators for splitting text
        )

    # The count_tokens method is no longer needed here, we will use self.llm_client.count_tokens

    def _get_translation_prompt_template(self, source_lang: str, target_lang: str) -> str:
        """Generates the detailed and optimized prompt template for the LLM."""
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

    def translate_text(self, full_text: str, source_lang: str, target_lang: str, MAX_TOKENS_PER_CALL=8000) -> Optional[
        str]:
        """Splits, translates, and joins the text using the LLM via the GeminiAI client."""
        logger.info(f"Starting translation from {source_lang} to {target_lang}...")

        # 1. Calculate the size of the base prompt and system prompt to determine space for content
        base_prompt_template = self._get_translation_prompt_template(source_lang, target_lang)
        # We use a short placeholder to estimate the prompt size without the actual chunk
        prompt_base_tokens = self.llm_client.count_tokens(base_prompt_template.format(text_chunk="[chunk]"))

        max_content_tokens = MAX_TOKENS_PER_CALL - prompt_base_tokens
        max_content_tokens = max(100, max_content_tokens)  # Ensure it's not negative or too small

        logger.info(f"  - Base Prompt Tokens (estimated): {prompt_base_tokens}")
        logger.info(f"  - Content Tokens per Chunk: {max_content_tokens}")
        logger.info(f"  - Total Limit per API Call (configured): {MAX_TOKENS_PER_CALL}")

        # Adjust the splitter's chunk size dynamically
        self.pre_translation_splitter._chunk_size = max_content_tokens

        # 2. Split the original text into chunks using the calculated size
        original_chunks = self.pre_translation_splitter.split_text(full_text)
        logger.info(
            f"  - Original text split into {len(original_chunks)} chunks for translation (target size: {max_content_tokens} tokens).")

        if not original_chunks:
            logger.warning("  - Warning: The original text resulted in 0 chunks after splitting. Check the input text.")
            return ""  # Return empty string if no chunks

        translated_text_parts = []
        total_chunks = len(original_chunks)
        for i, chunk in enumerate(original_chunks):
            current_chunk_tokens = self.llm_client.count_tokens(chunk)
            logger.info(f"  - Translating chunk {i + 1}/{total_chunks} ({current_chunk_tokens} tokens)...")

            # Check if the individual chunk exceeds the limit (rare with RecursiveCharacterTextSplitter, but possible)
            if current_chunk_tokens > max_content_tokens:
                logger.warning(
                    f"  - Warning: Chunk {i + 1} ({current_chunk_tokens} tokens) exceeds the calculated content limit ({max_content_tokens} tokens). This may cause errors. Attempting anyway.")

            # Generate the full prompt for this chunk
            prompt = base_prompt_template.format(text_chunk=chunk)

            try:
                # Call the model using the GeminiAI client's method
                # This method handles rate limiting and internal logging
                translated_chunk = self.llm_client.call_model(prompt)

                # Basic validation of the response
                if not translated_chunk or len(translated_chunk) < len(chunk) * 0.2:  # Very basic heuristic
                    logger.warning(
                        f"  - Warning: Possible issue with the translation of chunk {i + 1}. Response empty or very short.")
                    # Decide whether to retry, skip, or use the partial response
                    # For simplicity, we'll use it but print a warning.
                    # You could add retry logic here.
                    if not translated_chunk:
                        translated_chunk = f"[EMPTY_TRANSLATION_CHUNK_{i + 1}]"  # Add marker if empty

                translated_text_parts.append(translated_chunk)
                # We don't need to print success here, call_model already does.
                # logger.info(f"  - Chunk {i + 1}/{total_chunks} translated.")

            except Exception as e:
                # The call_model method should already log errors, but we can add context
                logger.error(f"Error during processing of chunk {i + 1} in TranslatorAgent: {e}")
                # Option: add an error marker and continue, or stop the process
                translated_text_parts.append(f"[TRANSLATION_ERROR_CHUNK_{i + 1}]")
                # return None # Uncomment if you prefer to stop on error

        logger.info("Translation of all chunks completed.")
        # Join the translated chunks. Use double newline as a standard separator.
        full_translated_text = "\n\n".join(translated_text_parts)
        # Final cleanup of possible error markers or excessive newlines
        full_translated_text = re.sub(r'\n{3,}', '\n\n', full_translated_text).strip()
        return full_translated_text
