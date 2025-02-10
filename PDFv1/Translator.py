import logging
import re
from typing import Optional

from langchain_text_splitters import RecursiveCharacterTextSplitter

from LLM.GeminiAI import GeminiAI

# Configure logging
logger = logging.getLogger(__name__)


class TranslatorAgent:
    # Modificado para aceptar una instancia de GeminiAI
    def __init__(self, MAX_TOKENS_PER_CALL=8000):
        self.llm_client = GeminiAI() # Guarda la instancia del cliente LLM

        # Splitter para dividir el texto ANTES de la traducción si excede el límite
        # Usará la función count_tokens del cliente LLM proporcionado
        self.pre_translation_splitter = RecursiveCharacterTextSplitter(
            # El tamaño del chunk debe ser menor que el límite total de la API,
            # considerando el system prompt y el prompt de usuario base.
            # Calcularemos esto dinámicamente en translate_text.
            chunk_size=MAX_TOKENS_PER_CALL, # Valor inicial, se ajustará
            chunk_overlap=0, # Un solapamiento mayor puede ayudar con el contexto entre chunks
            length_function=self.llm_client.count_tokens, # Usa el contador de tokens del cliente Gemini
            separators=["\n\n", "\n", ". ", ", ", " ", ""] # Separadores comunes para dividir texto
        )

    # El método count_tokens ya no es necesario aquí, usaremos self.llm_client.count_tokens

    def _get_translation_prompt_template(self, source_lang: str, target_lang: str) -> str:
        """Genera la plantilla del prompt detallado para el LLM, sin el texto."""
        # ESTE PROMPT ES CRUCIAL - AJÚSTALO SEGÚN SEA NECESARIO
        # Se ha movido la parte variable {text_chunk} fuera para calcular el tamaño base
        prompt_template = f"""
        Eres un traductor experto y editor multilingüe especializado en literatura, incluyendo novelas ligeras japonesas, chinas y coreanas, así como ficción occidental.

        Tarea Principal: Traduce el siguiente texto del {source_lang} al {target_lang}.

        Texto a procesar:
        \"\"\"
        {{text_chunk}}
        \"\"\"

        Instrucciones Detalladas (Sigue estrictamente estos pasos):

        1.  **Análisis Inicial y Coherencia:** Lee el texto completo. Si detectas partes gravemente incoherentes, corruptas o sin sentido (más allá de posibles errores de OCR o extracción), intenta inferir el significado correcto basándote en el contexto circundante. Si es imposible, traduce la parte problemática lo mejor posible indicando la incertidumbre si es necesario, pero **NO** inventes contenido extenso.
        2.  **Limpieza Preliminar:** Identifica y **ELIMINA** completamente cualquier texto que parezca ser un encabezado (ej. nombre del libro/capítulo repetido en cada página), pie de página (ej. numeración de página, avisos repetitivos), o números de página sueltos que interrumpan el flujo del texto narrativo. **NO** elimines los números de capítulo o títulos de sección que formen parte del contenido real.
        3.  **Análisis Gramatical y Corrección (Idioma Origen):** Antes de traducir, revisa la gramática y la estructura del texto en {source_lang}. Corrige errores obvios de puntuación, sintaxis o palabras mal escritas que puedan haber surgido de la extracción (OCR/conversión). Si hay frases incompletas, intenta completarlas basándote en el contexto inmediato si es claro, de lo contrario, tradúcelas tal como están. **NO** reescribas el estilo del autor.
        4.  **Traducción Fiel:** Realiza la traducción al {target_lang}. Mantén el tono, estilo y significado del texto original lo más fielmente posible.
            * **Modismos y Expresiones Culturales:** Traduce los modismos y referencias culturales de forma que tengan sentido en {target_lang}. Si no hay un equivalente directo, usa una explicación concisa o una adaptación cultural apropiada, manteniendo el espíritu original. Evita traducciones literales sin sentido. Para novelas J/C/K, presta atención a los honoríficos y términos específicos, traduciéndolos consistentemente (ej., 'senpai' puede quedarse como 'senpai' o adaptarse según el contexto).
            * **Nombres Propios:** Mantén los nombres de personajes y lugares tal como están en el original, a menos que tengan una forma estándar establecida en {target_lang} (ej., London -> Londres).
        5.  **Validación Gramatical y Puntuación (Idioma Destino):** Revisa minuciosamente la gramática, la ortografía y la puntuación del texto traducido en {target_lang}. Asegúrate de que las frases sean fluidas y naturales en el idioma de destino. Corrige cualquier error manteniendo parrafos coherentes eliminando saltos de linea innecesarios.
        6.  **Limpieza Final:** Revisa el texto traducido final y **ELIMINA** cualquier sección que claramente sea un índice, tabla de contenidos, página de copyright, bibliografía, notas del traductor original (a menos que aporten contexto crucial), o publicidad que no forme parte de la narrativa.
        7.  **Formato:** Devuelve ÚNICAMENTE el texto traducido y limpio, sin ningún comentario adicional, saludo, o explicación tuya fuera del propio texto traducido. Mantén los saltos de párrafo del texto original donde sea apropiado para la fluidez en {target_lang}.

        Idioma Origen: {source_lang}
        Idioma Destino: {target_lang}

        Texto Traducido y Limpio:
        """
        return prompt_template

    def translate_text(self, full_text: str, source_lang: str, target_lang: str, MAX_TOKENS_PER_CALL=8000) -> Optional[str]:
        """Divide, traduce y une el texto usando el LLM a través del cliente GeminiAI."""
        logger.info(f"Iniciando traducción de {source_lang} a {target_lang}...")

        # 1. Calcular el tamaño del prompt base y el system prompt para determinar el espacio para el contenido
        base_prompt_template = self._get_translation_prompt_template(source_lang, target_lang)
        # Usamos un placeholder corto para estimar el tamaño del prompt sin el chunk real
        prompt_base_tokens = self.llm_client.count_tokens(base_prompt_template.format(text_chunk="[chunk]"))

        max_content_tokens = MAX_TOKENS_PER_CALL - prompt_base_tokens  # Opción 2: Buffer fijo
        max_content_tokens = max(100, max_content_tokens)  # Asegurar que no sea negativo o muy pequeño

        logger.info(f"  - Tokens Prompt Base (estimado): {prompt_base_tokens}")
        logger.info(f"  - Tokens Montenido por Chunk: {max_content_tokens}")
        logger.info(f"  - Límite Total por Llamada API (configurado): {MAX_TOKENS_PER_CALL}")


        # Ajustar el tamaño del chunk del splitter dinámicamente
        self.pre_translation_splitter._chunk_size = max_content_tokens

        # 2. Dividir el texto original en chunks usando el tamaño calculado
        original_chunks = self.pre_translation_splitter.split_text(full_text)
        logger.info(f"  - Texto original dividido en {len(original_chunks)} chunks para traducción (tamaño objetivo: {max_content_tokens} tokens).")

        if not original_chunks:
             print("  - Advertencia: El texto original resultó en 0 chunks después de dividir. Verifique el texto de entrada.")
             return "" # Devolver cadena vacía si no hay chunks

        translated_text_parts = []
        total_chunks = len(original_chunks)
        for i, chunk in enumerate(original_chunks):
            current_chunk_tokens = self.llm_client.count_tokens(chunk)
            logger.info(f"  - Traduciendo chunk {i + 1}/{total_chunks} ({current_chunk_tokens} tokens)...")

            # Verificar si el chunk individual excede el límite (raro con RecursiveCharacterTextSplitter, pero posible)
            if current_chunk_tokens > max_content_tokens:
                logger.warning(
                    f"  - Advertencia: Chunk {i + 1} ({current_chunk_tokens} tokens) excede el límite de contenido calculado ({max_content_tokens} tokens). Esto puede causar errores. Se intentará de todos modos.")

            # Generar el prompt completo para este chunk
            prompt = base_prompt_template.format(text_chunk=chunk)

            try:
                # Llamada al modelo usando el método del cliente GeminiAI
                # Este método maneja el rate limiting y logging interno
                translated_chunk = self.llm_client.call_model(prompt)

                # Validación básica de la respuesta
                if not translated_chunk or len(translated_chunk) < len(chunk) * 0.2: # Heurística muy básica
                    logger.warning(
                        f"  - Advertencia: Posible problema con la traducción del chunk {i + 1}. Respuesta vacía o muy corta.")
                    # Decide si reintentar, omitir, o usar la respuesta parcial
                    # Por simplicidad, la usaremos pero imprimimos advertencia.
                    # Podrías añadir lógica de reintento aquí.
                    if not translated_chunk:
                         translated_chunk = f"[TRADUCCION_VACIA_CHUNK_{i+1}]" # Añadir marcador si está vacía


                translated_text_parts.append(translated_chunk)
                # No necesitamos imprimir éxito aquí, call_model ya lo hace.
                # print(f"  - Chunk {i + 1}/{total_chunks} traducido.")

            except Exception as e:
                # El método call_model ya debería imprimir errores, pero podemos añadir contexto
                logger.error(f"Error durante el procesamiento del chunk {i + 1} en TranslatorAgent: {e}")
                # Opción: añadir un marcador de error y continuar, o detener el proceso
                translated_text_parts.append(f"[ERROR_TRADUCCION_CHUNK_{i + 1}]")
                # return None # Descomentar si prefieres detener en caso de error

        logger.info("Traducción de todos los chunks completada.")
        # Unir los chunks traducidos. Usar doble salto de línea como separador estándar.
        full_translated_text = "\n\n".join(translated_text_parts)
        # Limpieza final de posibles marcadores de error o saltos excesivos
        full_translated_text = re.sub(r'\n{3,}', '\n\n', full_translated_text).strip()
        return full_translated_text