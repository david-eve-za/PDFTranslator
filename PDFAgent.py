import argparse
import logging
import os
import sys
from pathlib import Path
from typing import Optional, List

from AudioGenerator import AudioGenerator  # Asumimos que AudioGenerator.py existe y es adaptable
from PDFv1.FileFinder import FilesFinder  # Asumimos que PDFv1/FileFinder.py existe
from PDFv1.TextExtractor import TextExtractorAgent  # Asumimos que PDFv1/TextExtractor.py existe
from PDFv1.Translator import TranslatorAgent  # Asumimos que PDFv1/Translator.py existe
from VideoGenerator import VideoGenerator

import warnings

warnings.filterwarnings("ignore", category=UserWarning, message=".*pkg_resources is deprecated.*")

# --- Constants ---
LOG_FILE_NAME = "PDFAgent.log"
DEFAULT_OUTPUT_SUBDIR = "audiobooks"
DEFAULT_FILE_TYPE_TO_PROCESS = "pdf"  # Assuming FilesFinder supports "pdf" and "epub"


# --- Logging Setup ---
def setup_logging():
    """Configures logging to stream to stdout and a log file."""
    logging.basicConfig(format='%(asctime)s,%(msecs)03d %(name)s %(levelname)s %(message)s',
                        datefmt='%Y-%m-%d %H:%M:%S',
                        level=logging.INFO,
                        handlers=[
                            logging.StreamHandler(sys.stdout),
                                  logging.FileHandler(LOG_FILE_NAME)
                                  ]
                        )


# --- Argument Parsing ---
def parse_arguments() -> argparse.Namespace:
    """Parses command-line arguments."""
    parser = argparse.ArgumentParser(description="Generador de Audiolibros desde PDF/EPUB con Traducción AI")
    parser.add_argument("input_path", type=Path,
                        help="Ruta al directorio que contiene los archivos a procesar (PDF, EPUB, etc.).")
    # Se elimina el argumento -o/--output_dir. La salida ahora es relativa a cada archivo.
    parser.add_argument("-sl", "--source_lang", default="en",
                        help="Idioma de origen (código ISO 639-1, ej: en, ja, zh, ko). Por defecto: en (inglés).")
    parser.add_argument("-tl", "--target_lang", default="es",
                        help="Idioma de destino (código ISO 639-1, ej: es, en). Por defecto: es (español).")
    parser.add_argument("--output_format", default="m4a", choices=['m4a', 'mp3', 'aiff', 'wav'],
                        help="Formato del archivo de audio final (por defecto: m4a). MP3 requiere re-codificación.")
    parser.add_argument("--voice", default="Paulina", choices=["Monica", "Paulina", "Jorge"],
                        help="Nombre exacto de la voz de macOS 'say' a usar para el idioma destino (ej: Monica, Paulina, Jorge). Si no se especifica, se usa un valor por defecto para español o la voz del sistema.")
    return parser.parse_args()


# --- File Processing Logic ---
def process_single_file(file_path: str,
                        output_subdir_name: str,
                        source_lang: str,
                        target_lang: str,
                        output_format: str,
                        extractor: TextExtractorAgent,  # Idealmente, sería ITextExtractor
                        translator: TranslatorAgent,  # Idealmente, sería ITranslator
                        audio_generator: AudioGenerator,  # Idealmente, sería IAudioGenerator
                        video_generator: VideoGenerator
                        ) -> bool:
    """
    Processes a single input file: extracts text, translates, and generates audio.
    The audio output will be in a subdirectory (output_subdir_name) relative to the file's location.

    Args:
        file_path: Path to the input file.
        output_subdir_name: Name of the subdirectory (e.g., "audiobooks") for the output.
        source_lang: Source language code.
        target_lang: Target language code.
        output_format: Desired audio output format.
        extractor: Instance of TextExtractorAgent (or an ITextExtractor implementation).
        translator: Instance of TranslatorAgent (or an ITranslator implementation).
        audio_generator: Instance of AudioGenerator (or an IAudioGenerator implementation),
                         assumed to be pre-configured with voice and language.

    Returns:
        True if processing was successful or file was skipped appropriately, False otherwise.
    """
    logging.info(f"\n--- Procesando archivo: {os.path.basename(file_path)} ---")

    # Determinar directorio de salida dinámico basado en la ruta del archivo de entrada
    try:
        # Usar abspath para asegurar que dirname funcione correctamente incluso si file_path es solo un nombre de archivo
        abs_file_path = os.path.abspath(file_path)
        file_parent_dir = os.path.dirname(abs_file_path)
        dynamic_output_dir = os.path.join(file_parent_dir, output_subdir_name)
        os.makedirs(dynamic_output_dir, exist_ok=True)
        logging.info(f"  - Directorio de salida para este archivo: {dynamic_output_dir}")
    except OSError as e:
        logging.error(
            f"  - Error al crear directorio de salida {dynamic_output_dir} para {os.path.basename(file_path)}: {e}")
        return False

    base_name = os.path.splitext(os.path.basename(file_path))[0]
    output_audio_filename = Path(os.path.join(dynamic_output_dir, f"{base_name}_{target_lang}.{output_format}"))

    if os.path.exists(output_audio_filename):
        logging.info(f"  - El archivo de audio ya existe: {output_audio_filename}. Saltando.")
        return True  # Considerado "manejado"

    # 1. Extraer texto
    original_text, images_list = extractor.extract_text(file_path)
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

    # 3. Generar audio
    try:
        logging.warning(
            "  - AudioGenerator no tiene el método 'generate_audio_to_file'. Se requiere adaptación de AudioGenerator.py para un mejor DIP o revertir su instanciación a este punto.")
        success = audio_generator.process_texts(text_content=translated_text,
                                                output_filename=output_audio_filename)  # Asumiendo que process_texts puede tomar output_filename

    except Exception as e:
        logging.error(f"  - Error durante la generación de audio para {os.path.basename(file_path)}: {e}")
        return False

    if success:
        logging.info(f"--- Procesamiento completado para: {os.path.basename(file_path)} ---")
        # video_generator.create_video_from_images_and_audio(image_paths=[str(img) for img in images_list],audio_path=str(output_audio_filename),output_video_path=str(output_audio_filename.with_suffix(".mp4")))
    else:
        logging.error(f"--- Procesamiento fallido para: {os.path.basename(file_path)} ---")
    return success


# --- Orquestador Principal ---
def main():
    """
    Orchestrates the process of finding files, extracting text,
    translating, and generating audiobooks.
    """
    setup_logging()
    args = parse_arguments()

    if not os.path.isdir(args.input_path):
        logging.error(f"El directorio de entrada no existe: {args.input_path}")
        return

    # Inicializar Agentes y Servicios
    # Estos se crean una vez y se inyectan donde sea necesario (DIP)
    finder = FilesFinder(args.input_path)
    extractor = TextExtractorAgent()  # Podría ser una factoría si hay múltiples tipos de extractores
    translator = TranslatorAgent(
        default_max_tokens_per_call=30000)  # Podría ser una factoría para diferentes servicios de traducción

    # Se instancia AudioGenerator aquí, asumiendo que su API lo permite (constructor general, método de proceso con ruta de salida).
    # Esto es una mejora para DIP. Si AudioGenerator DEBE tener final_output en su constructor,
    # entonces su instanciación debe ocurrir dentro de process_single_file.
    # Para "ofrecer mejoras", se asume que AudioGenerator puede ser refactorizado o ya es flexible.
    try:
        audio_generator_service = AudioGenerator(
            voice=args.voice
        )
    except Exception as e:
        logging.error(
            f"Error al inicializar AudioGenerator: {e}. Asegúrate de que AudioGenerator.py es compatible con la inicialización (voice, language).")
        return

    files_to_process: List[str] = finder.get_files(file_type=DEFAULT_FILE_TYPE_TO_PROCESS)
    if not files_to_process or len(files_to_process) == 0:
        logging.info(f"No se encontraron archivos .{DEFAULT_FILE_TYPE_TO_PROCESS} en '{args.input_path}'.")
        return

    video_gen = VideoGenerator()

    logging.info(f"Se encontraron {len(files_to_process)} archivo(s) .{DEFAULT_FILE_TYPE_TO_PROCESS} para procesar.")

    successful_files_count = 0
    failed_files_count = 0

    for file_path in files_to_process:
        # La voz ya está configurada en audio_generator_service
        # target_lang también está configurado en audio_generator_service, pero se pasa
        # porque es necesario para el nombre del archivo de salida y para el traductor.
        success = process_single_file(
            file_path=file_path,
            output_subdir_name=DEFAULT_OUTPUT_SUBDIR,
            source_lang=args.source_lang,
            target_lang=args.target_lang,
            output_format=args.output_format,
            extractor=extractor,
            translator=translator,
            audio_generator=audio_generator_service,
            video_generator=video_gen
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
