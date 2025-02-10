import argparse
import logging
import os
import sys

from AudioGenerator import AudioGenerator
from PDFv1.FileFinder import FilesFinder
from PDFv1.TextExtractor import TextExtractorAgent
from PDFv1.Translator import TranslatorAgent

logging.basicConfig(format='%(asctime)s,%(msecs)03d %(name)s %(levelname)s %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S',
                    level=logging.INFO,
                    handlers=[logging.StreamHandler(sys.stdout), logging.FileHandler('PDFAgent.log')]
                    )


# --- Orquestador Principal ---
def main():
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

    args = parser.parse_args()

    # Validar directorio de entrada
    if not os.path.isdir(args.input_path):
        logging.error(f"El directorio de entrada no existe: {args.input_path}")
        return

    # Crear directorio de salida si no existe
    if ".".__eq__(args.output_dir):
        args.output_dir = os.path.join(args.input_path, "audiobooks")
    os.makedirs(args.output_dir, exist_ok=True)

    # Inicializar Agentes
    finder = FilesFinder(args.input_path)
    extractor = TextExtractorAgent()
    translator = TranslatorAgent()  # Usará GEMINI_MODEL_NAME

    # Procesar cada archivo encontrado
    files_to_process = finder.get_files(file_type="epub")
    if not files_to_process:
        return  # Salir si no hay archivos

    for file_path in files_to_process:
        logging.info(f"\n--- Procesando archivo: {os.path.basename(file_path)} ---")
        base_name = os.path.splitext(os.path.basename(file_path))[0]
        output_audio_filename = os.path.join(args.output_dir, f"{base_name}_{args.target_lang}.{args.output_format}")
        if os.path.exists(output_audio_filename):
            logging.info(f"  - El archivo de audio ya existe: {output_audio_filename}")
            continue

        # Pasar código de idioma y voz opcional al agente de audio
        audio_processor = AudioGenerator(final_output=output_audio_filename)

        # 1. Extraer texto
        original_text = extractor.extract_text(file_path)
        if not original_text or not original_text.strip():
            logging.warning("  - No se pudo extraer texto o el texto está vacío. Saltando archivo.")
            continue
        logging.info(f"  - Texto original extraído (longitud: {len(original_text)} caracteres)")

        # 2. Traducir texto
        #    La validación, limpieza, corrección y traducción ocurren dentro de este método usando el LLM
        translated_text = translator.translate_text(original_text, args.source_lang, args.target_lang)
        if not translated_text or not translated_text.strip():
            logging.warning("  - La traducción falló o resultó en texto vacío. Saltando archivo.")
            continue
        logging.info(f"  - Texto traducido y limpiado (longitud: {len(translated_text)} caracteres)")

        # Guardar texto traducido (opcional, útil para depuración)
        # base_name = os.path.splitext(os.path.basename(file_path))[0]
        # translated_txt_path = os.path.join(args.output_dir, f"{base_name}_translated_{args.target_lang}.txt")
        # try:
        #     with open(translated_txt_path, 'w', encoding='utf-8') as f:
        #         f.write(translated_text)
        #     print(f"  - Texto traducido guardado en: {translated_txt_path}")
        # except Exception as e:
        #     logging.warning(f"  - Advertencia: No se pudo guardar el texto traducido: {e}")

        # 3. Generar audiolibro desde texto traducido
        success = audio_processor.process_texts(translated_text)

        if success:
            logging.info(f"--- Procesamiento completado para: {os.path.basename(file_path)} ---")
        else:
            logging.error(f"--- Procesamiento fallido para: {os.path.basename(file_path)} ---")

    logging.info("\nProceso finalizado para todos los archivos encontrados.")


if __name__ == "__main__":
    main()
