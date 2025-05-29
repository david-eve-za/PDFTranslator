import argparse
import logging
import os
import sys
from typing import Optional, List

from AudioGenerator import AudioGenerator  # Assuming AudioGenerator.py exists
from PDFv1.FileFinder import FilesFinder  # Assuming PDFv1/FileFinder.py exists
from PDFv1.TextExtractor import TextExtractorAgent  # Assuming PDFv1/TextExtractor.py exists
from PDFv1.Translator import TranslatorAgent  # Assuming PDFv1/Translator.py exists

# --- Constants ---
LOG_FILE_NAME = "PDFAgent.log"
DEFAULT_OUTPUT_SUBDIR = "audiobooks"
DEFAULT_FILE_TYPE_TO_PROCESS = "epub"  # Or "pdf" or make it an argument


# --- Logging Setup ---
def setup_logging():
    """Configures logging to stream to stdout and a log file."""
    logging.basicConfig(format='%(asctime)s,%(msecs)03d %(name)s %(levelname)s %(message)s',
                        datefmt='%Y-%m-%d %H:%M:%S',
                        level=logging.INFO,
                        handlers=[logging.StreamHandler(sys.stdout),
                                  logging.FileHandler(LOG_FILE_NAME)]
                        )


# --- Argument Parsing ---
def parse_arguments() -> argparse.Namespace:
    """Parses command-line arguments."""
    parser = argparse.ArgumentParser(description="Generador de Audiolibros desde PDF/EPUB con Traducción AI")
    parser.add_argument("input_path", help="Ruta al directorio que contiene los archivos PDF y EPUB.")
    parser.add_argument("-o", "--output_dir", default=".",
                        help="Directorio donde guardar los audiolibros generados (por defecto: directorio actual).")
    parser.add_argument("-sl", "--source_lang", default="en",
                        help="Idioma de origen (código ISO 639-1, ej: en, ja, zh, ko). Por defecto: en (inglés).")
    parser.add_argument("-tl", "--target_lang", default="es",
                        help="Idioma de destino (código ISO 639-1, ej: es, en). Por defecto: es (español).")
    parser.add_argument("--output_format", default="m4a", choices=['m4a', 'mp3', 'aiff', 'wav'],
                        help="Formato del archivo de audio final (por defecto: m4a). MP3 requiere re-codificación.")
    parser.add_argument("--voice",
                        help="Nombre exacto de la voz de macOS 'say' a usar para el idioma destino (ej: Monica, Paulina, Jorge). Si no se especifica, se usa un valor por defecto para español o la voz del sistema.")
    return parser.parse_args()


# --- File Processing Logic ---
def process_single_file(file_path: str,
                        output_dir: str,
                        source_lang: str,
                        target_lang: str,
                        output_format: str,
                        voice: Optional[str],
                        extractor: TextExtractorAgent,
                        translator: TranslatorAgent) -> bool:
    """
    Processes a single input file: extracts text, translates, and generates audio.

    Args:
        file_path: Path to the input file.
        output_dir: Directory to save the generated audiobook.
        source_lang: Source language code.
        target_lang: Target language code.
        output_format: Desired audio output format.
        voice: Optional voice name for text-to-speech.
        extractor: Instance of TextExtractorAgent.
        translator: Instance of TranslatorAgent.

    Returns:
        True if processing was successful or file was skipped appropriately, False otherwise.
    """
    logging.info(f"\n--- Procesando archivo: {os.path.basename(file_path)} ---")
    base_name = os.path.splitext(os.path.basename(file_path))[0]
    output_audio_filename = os.path.join(output_dir, f"{base_name}_{target_lang}.{output_format}")

    if os.path.exists(output_audio_filename):
        logging.info(f"  - El archivo de audio ya existe: {output_audio_filename}. Saltando.")
        return True  # Considered "handled"

    # Assuming AudioGenerator can accept voice and language for configuration.
    # This makes the use of the --voice argument explicit.
    # If AudioGenerator's API is different, this instantiation needs to be adjusted.
    audio_processor = AudioGenerator(
        final_output=output_audio_filename,
        voice=voice,  # Pass the voice from arguments
        language=target_lang  # Pass the target language
    )

    # 1. Extraer texto
    original_text = extractor.extract_text(file_path)
    if not original_text or not original_text.strip():
        logging.warning(
            f"  - No se pudo extraer texto o el texto está vacío para {os.path.basename(file_path)}. Saltando archivo.")
        return False
    logging.info(f"  - Texto original extraído (longitud: {len(original_text)} caracteres)")

    # 2. Traducir texto
    translated_text = translator.translate_text(original_text, source_lang, target_lang)
    if not translated_text or not translated_text.strip():
        logging.warning(
            f"  - La traducción falló o resultó en texto vacío para {os.path.basename(file_path)}. Saltando archivo.")
        return False
    logging.info(f"  - Texto traducido y limpiado (longitud: {len(translated_text)} caracteres)")

    # Opcional: Guardar texto traducido (útil para depuración)
    # Consider making this a command-line option if frequently needed.
    # translated_txt_path = os.path.join(output_dir, f"{base_name}_translated_{target_lang}.txt")
    # try:
    #     with open(translated_txt_path, 'w', encoding='utf-8') as f:
    #         f.write(translated_text)
    #     logging.info(f"  - Texto traducido guardado en: {translated_txt_path}") # Changed print to logging.info
    # except Exception as e:
    #     logging.warning(f"  - Advertencia: No se pudo guardar el texto traducido: {e}")

    # 3. Generar audiolibro desde texto traducido
    success = audio_processor.process_texts(translated_text)

    if success:
        logging.info(f"--- Procesamiento completado para: {os.path.basename(file_path)} ---")
    else:
        logging.error(f"--- Procesamiento fallido para: {os.path.basename(file_path)} ---")
    return success


# --- Orquestador Principal ---
def main():
    """
    Orchestrates the process of finding PDF/EPUB files, extracting text,
    translating, and generating audiobooks.
    """
    setup_logging()
    args = parse_arguments()

    # Validar directorio de entrada
    if not os.path.isdir(args.input_path):
        logging.error(f"El directorio de entrada no existe: {args.input_path}")
        return

    # Determinar y crear directorio de salida
    output_directory = args.output_dir
    if output_directory == ".":  # Standard string comparison
        output_directory = os.path.join(args.input_path, DEFAULT_OUTPUT_SUBDIR)

    try:
        os.makedirs(output_directory, exist_ok=True)
        logging.info(f"Directorio de salida: {output_directory}")
    except OSError as e:
        logging.error(f"No se pudo crear el directorio de salida {output_directory}: {e}")
        return

    # Inicializar Agentes
    finder = FilesFinder(args.input_path)
    extractor = TextExtractorAgent()
    translator = TranslatorAgent()  # Comment from original: Usará GEMINI_MODEL_NAME

    # Procesar cada archivo encontrado
    files_to_process: List[str] = finder.get_files(file_type=DEFAULT_FILE_TYPE_TO_PROCESS)
    if not files_to_process:
        logging.info(f"No se encontraron archivos .{DEFAULT_FILE_TYPE_TO_PROCESS} en '{args.input_path}'.")
        return

    logging.info(f"Se encontraron {len(files_to_process)} archivo(s) .{DEFAULT_FILE_TYPE_TO_PROCESS} para procesar.")

    successful_files_count = 0
    failed_files_count = 0

    for file_path in files_to_process:
        success = process_single_file(
            file_path=file_path,
            output_dir=output_directory,
            source_lang=args.source_lang,
            target_lang=args.target_lang,
            output_format=args.output_format,
            voice=args.voice,
            extractor=extractor,
            translator=translator
        )
        if success:
            successful_files_count += 1
        else:
            failed_files_count += 1

    logging.info("\n--- Resumen del Proceso ---")
    logging.info(f"Procesamiento finalizado.")
    logging.info(f"Archivos procesados/saltados exitosamente: {successful_files_count}")
    logging.info(f"Archivos con fallos en el procesamiento: {failed_files_count}")
    logging.info(f"Los archivos de registro se encuentran en: {LOG_FILE_NAME}")


if __name__ == "__main__":
    main()