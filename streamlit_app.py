import streamlit as st
import os
from typing import Optional, List

# Asegúrate de que estos módulos sean importables.
# Deben estar en el mismo directorio o en una ruta accesible por PYTHONPATH.
try:
    from AudioGenerator import AudioGenerator
    from PDFv1.FileFinder import FilesFinder
    from PDFv1.TextExtractor import TextExtractorAgent
    from PDFv1.Translator import TranslatorAgent
except ImportError as e:
    st.error(f"Error al importar módulos necesarios: {e}")
    st.error(
        "Asegúrate de que AudioGenerator.py y la carpeta PDFv1 (con __init__.py) estén en la misma ubicación que streamlit_app.py o en PYTHONPATH.")
    st.stop()

# --- Constantes (puedes ajustarlas o importarlas si es necesario) ---
DEFAULT_OUTPUT_SUBDIR = "audiobooks"


# DEFAULT_FILE_TYPE_TO_PROCESS ya no es una constante fija, se selecciona en la UI.

# --- Lógica de Procesamiento de Archivo Individual (adaptada para Streamlit) ---
def process_single_file_st(file_path: str,
                           output_dir: str,
                           source_lang: str,
                           target_lang: str,
                           output_format: str,
                           voice: Optional[str],
                           extractor: TextExtractorAgent,
                           translator: TranslatorAgent) -> bool:
    """
    Procesa un solo archivo: extrae texto, traduce y genera audio.
    Muestra el progreso y los resultados usando los componentes de Streamlit.
    """
    st.info(f"--- Procesando archivo: {os.path.basename(file_path)} ---")
    base_name = os.path.splitext(os.path.basename(file_path))[0]
    output_audio_filename = os.path.join(output_dir, f"{base_name}_{target_lang}.{output_format}")

    if os.path.exists(output_audio_filename):
        st.info(f"  - El archivo de audio ya existe: {output_audio_filename}. Saltando.")
        return True  # Considerado "manejado"

    try:
        audio_processor = AudioGenerator(
            final_output=output_audio_filename,
            voice=voice,
            language=target_lang
        )
    except Exception as e:
        st.error(f"  - Error al inicializar AudioGenerator para {os.path.basename(file_path)}: {e}")
        return False

    # 1. Extraer texto
    try:
        original_text = extractor.extract_text(file_path)
        if not original_text or not original_text.strip():
            st.warning(
                f"  - No se pudo extraer texto o el texto está vacío para {os.path.basename(file_path)}. Saltando archivo.")
            return False
        st.info(f"  - Texto original extraído (longitud: {len(original_text)} caracteres)")
    except Exception as e:
        st.error(f"  - Error al extraer texto de {os.path.basename(file_path)}: {e}")
        return False

    # 2. Traducir texto
    try:
        translated_text = translator.translate_text(original_text, source_lang, target_lang)
        if not translated_text or not translated_text.strip():
            st.warning(
                f"  - La traducción falló o resultó en texto vacío para {os.path.basename(file_path)}. Saltando archivo.")
            return False
        st.info(f"  - Texto traducido y limpiado (longitud: {len(translated_text)} caracteres)")
    except Exception as e:
        st.error(f"  - Error al traducir texto de {os.path.basename(file_path)}: {e}")
        return False

    # Opcional: Guardar texto traducido (útil para depuración)
    # translated_txt_path = os.path.join(output_dir, f"{base_name}_translated_{target_lang}.txt")
    # try:
    #     with open(translated_txt_path, 'w', encoding='utf-8') as f:
    #         f.write(translated_text)
    #     st.info(f"  - Texto traducido guardado en: {translated_txt_path}")
    # except Exception as e:
    #     st.warning(f"  - Advertencia: No se pudo guardar el texto traducido: {e}")

    # 3. Generar audiolibro desde texto traducido
    try:
        success = audio_processor.process_texts(translated_text)
        if success:
            st.success(f"--- Procesamiento completado para: {os.path.basename(file_path)} ---")
            st.markdown(f"**Archivo generado:** `{output_audio_filename}`")
            # Considerar st.download_button si los archivos son accesibles/pequeños
        else:
            st.error(f"--- Procesamiento fallido (AudioGenerator) para: {os.path.basename(file_path)} ---")
        return success
    except Exception as e:
        st.error(f"  - Error durante la generación de audio para {os.path.basename(file_path)}: {e}")
        return False


# --- Función Principal de la Aplicación Streamlit ---
def run_app():
    st.set_page_config(page_title="Generador de Audiolibros AI", layout="wide")
    st.title("📚 Generador de Audiolibros con Traducción AI 🎧")
    st.markdown("Procesa tus archivos PDF/EPUB, tradúcelos y conviértelos en audiolibros.")

    # --- Configuración en la Barra Lateral ---
    st.sidebar.header("⚙️ Configuración")
    input_path = st.sidebar.text_input("Directorio de Entrada de Libros", placeholder="Ej: /ruta/a/tus/libros")

    default_output_dir_placeholder = "Directorio actual o <Directorio de Entrada>/audiobooks"
    if input_path and os.path.isdir(input_path):  # Actualiza dinámicamente el placeholder
        default_output_dir_placeholder = os.path.join(input_path, DEFAULT_OUTPUT_SUBDIR)

    output_dir_input = st.sidebar.text_input(
        "Directorio de Salida para Audiolibros (opcional)",
        placeholder=default_output_dir_placeholder,
        help=f"Si se deja vacío y el directorio de entrada es válido, se usará '{default_output_dir_placeholder}'. Si no, se usará el directorio actual del script."
    )

    source_lang = st.sidebar.text_input("Idioma de Origen (código ISO)", "en", help="Ej: en, es, ja, zh, ko, fr, de")
    target_lang = st.sidebar.text_input("Idioma de Destino (código ISO)", "es", help="Ej: es, en, ja, zh, ko, fr, de")

    file_type_to_process = st.sidebar.selectbox(
        "Tipo de archivo a procesar",
        ("epub", "pdf"),
        index=0,  # 'epub' por defecto
        help="Selecciona el tipo de archivo que quieres buscar y procesar."
    )

    output_format = st.sidebar.selectbox(
        "Formato de Audio de Salida",
        ('m4a', 'mp3', 'aiff', 'wav'),
        index=0,  # 'm4a' por defecto
        help="MP3 puede requerir re-codificación y tardar más."
    )
    raw_voice = st.sidebar.text_input(
        "Voz de macOS (opcional)",
        placeholder="Ej: Monica (es), Paulina (es), Jorge (es)",
        help="Nombre exacto de la voz de macOS 'say'. Si no se especifica, se usa un valor por defecto para el idioma destino."
    )

    # --- Área de Procesamiento ---
    st.header("🚀 Procesamiento")
    if st.button(f"Generar Audiolibros de archivos .{file_type_to_process}"):
        if not input_path:
            st.error("Por favor, especifica el Directorio de Entrada de Libros.")
            return  # st.stop() también funciona aquí

        if not os.path.isdir(input_path):
            st.error(f"El directorio de entrada no existe o no es válido: {input_path}")
            return

        # Determinar y crear directorio de salida
        output_directory = output_dir_input.strip()
        if not output_directory:
            if input_path and os.path.isdir(input_path):  # Re-check input_path validez
                output_directory = os.path.join(input_path, DEFAULT_OUTPUT_SUBDIR)
            else:
                output_directory = "."  # Fallback al directorio actual del script

        try:
            os.makedirs(output_directory, exist_ok=True)
            st.info(f"Directorio de salida configurado en: {os.path.abspath(output_directory)}")
        except OSError as e:
            st.error(f"No se pudo crear el directorio de salida {output_directory}: {e}")
            return

        # Inicializar Agentes
        try:
            finder = FilesFinder(input_path)
            extractor = TextExtractorAgent()
            # Asume que TranslatorAgent se configura internamente (ej. variables de entorno para API keys)
            translator = TranslatorAgent()
        except Exception as e:
            st.error(f"Error al inicializar los agentes de procesamiento: {e}")
            st.error("Verifica la configuración de los agentes (ej. API keys para TranslatorAgent).")
            # import traceback
            # st.text_area("Detalles del error:", traceback.format_exc(), height=150)
            return

        files_to_process: List[str] = finder.get_files(file_type=file_type_to_process)

        if not files_to_process:
            st.warning(f"No se encontraron archivos .{file_type_to_process} en '{input_path}'.")
            return

        st.info(f"Se encontraron {len(files_to_process)} archivo(s) .{file_type_to_process} para procesar.")

        successful_files_count = 0
        failed_files_count = 0

        progress_bar = st.progress(0)
        status_text = st.empty()  # Para mostrar el archivo actual

        processed_voice = raw_voice.strip() if raw_voice else None

        for i, file_path in enumerate(files_to_process):
            status_text.text(f"Procesando archivo {i + 1}/{len(files_to_process)}: {os.path.basename(file_path)}")

            # Usar un expander para los logs de cada archivo
            with st.expander(f"Detalles del procesamiento para: {os.path.basename(file_path)}", expanded=False):
                success = process_single_file_st(
                    file_path=file_path,
                    output_dir=output_directory,
                    source_lang=source_lang,
                    target_lang=target_lang,
                    output_format=output_format,
                    voice=processed_voice,
                    extractor=extractor,
                    translator=translator
                )
            if success:
                successful_files_count += 1
            else:
                failed_files_count += 1
            progress_bar.progress((i + 1) / len(files_to_process))

        status_text.text("Procesamiento de todos los archivos completado.")
        st.markdown("---")
        st.subheader("📊 Resumen del Proceso")
        st.success(f"Archivos procesados/saltados exitosamente: {successful_files_count}")
        if failed_files_count > 0:
            st.error(f"Archivos con fallos en el procesamiento: {failed_files_count}")
        else:
            st.info(f"Archivos con fallos en el procesamiento: {failed_files_count}")

        # Si mantienes el logging a archivo del script original, puedes mencionarlo:
        # log_file_path = os.path.join(os.getcwd(), "PDFAgent.log") # Asumiendo que se crea en CWD
        # st.info(f"Para registros técnicos detallados, consulta el archivo: {log_file_path}")


if __name__ == "__main__":
    run_app()