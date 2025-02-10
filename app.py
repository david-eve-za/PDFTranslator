import hashlib

import pandas as pd
import streamlit as st

from PDFv2 import PDFProcessor, TranslationEngine, TranslationState, TranslationError


class TranslationUI:
    def __init__(self):
        self.pdf_processor = PDFProcessor()
        self.current_state = None
        self._filename = None

    def render_interface(self):
        """Renderiza la interfaz principal"""
        st.title("PDF Translator Pro")
        uploaded_file = st.file_uploader("Subir documento PDF", type="pdf")

        if uploaded_file:
            self._filename = uploaded_file.name
            self._handle_file_upload(uploaded_file)
            self._render_translation_controls()
            self._render_progress()
            self._render_comparison_table()

    def _handle_file_upload(self, file):
        """Maneja la carga de nuevos archivos"""
        file_hash = hashlib.sha256(file.read()).hexdigest()
        file.seek(0)

        if not self.current_state or self.current_state.file_hash != file_hash:
            self.current_state = TranslationState(file_hash)

            if not self.current_state.state["content"]:
                with st.spinner("Analizando estructura del PDF..."):
                    self.current_state.state["content"] = self.pdf_processor.process_pdf(file)
                    self.current_state._save()

    def _render_translation_controls(self):
        """Muestra controles de traducción"""
        idiomas = {
            "Inglés": "en",
            "Español": "es",
            "Francés": "fr",
            "Alemán": "de",
            "Italiano": "it"
        }
        col1, col2, col3 = st.columns([2, 1, 1])
        with col1:
            src_lang = st.selectbox("Idioma Origen", list(idiomas.keys()), index=0)
            tgt_lang = st.selectbox("Idioma Destino", list(idiomas.keys()), index=1)

        with col2:
            if st.button("Iniciar/Reanudar", help="Comienza o continúa la traducción"):
                self._start_translation(src_lang, tgt_lang)

        with col3:
            if st.button("Reiniciar", type="secondary"):
                self.current_state.purge_state()
                st.rerun()

    def _start_translation(self, src_lang, tgt_lang):
        """Inicia el proceso de traducción"""
        translator = TranslationEngine(model_name="deepseek-r1:14b")
        # translator.build_context(self.current_state.state["content"])

        with st.status("Procesando...", expanded=True) as status:
            self._process_batches(translator, status)

    def _process_batches(self, translator, status):
        """Manejo seguro del proceso por lotes"""
        try:
            with status:
                progress_bar = st.progress(0)
                status_text = st.empty()

                total_items = len(self.current_state.state["content"])

                for item in self.current_state.state["content"]:
                    if item['metadata']['translated']:
                        continue

                    try:
                        translator.translate_item(item, self.current_state)
                        translated_count = sum(
                            1 for item in self.current_state.state["content"] if item['metadata']['translated'])
                        progress = translated_count / total_items
                        progress_bar.progress(progress)
                        status_text.text(f"Progreso: {translated_count}/{total_items} elementos")
                    except TranslationError as e:
                        self.current_state.set_error({
                            "type": "TranslationError",
                            "error": str(e)
                        })
                        status.update(label="Error en la traducción", state="error")
                        st.error(f"Error en la traducción: {str(e)}")
                        break

                # batch_size = 10
                # total_items = len(self.current_state.state["content"])
                #
                # for batch_start in range(self.current_state.state["current_position"], total_items, batch_size):
                #     batch_end = min(batch_start + batch_size, total_items)
                #     batch = self.current_state.state["content"][batch_start:batch_end]
                #
                #     try:
                #         translator.translate_batch(batch, self.current_state)
                #         self.current_state.update_position(batch_end)
                #
                #         translated_count = sum(
                #             1 for item in self.current_state.state["content"] if item['metadata']['translated'])
                #         progress = translated_count / total_items
                #         progress_bar.progress(progress)
                #         status_text.text(f"Progreso: {translated_count}/{total_items} elementos")
                #
                #     except TranslationError as e:
                #         self.current_state.set_error({
                #             "batch_start": batch_start,
                #             "batch_end": batch_end,
                #             "error": str(e)
                #         })
                #         status.update(label="Error en lote", state="error")
                #         st.error(f"Error en lote {batch_start}-{batch_end}: {str(e)}")
                #         break

                if all(item['metadata']['translated'] for item in self.current_state.state["content"]):
                    status.update(label="Traducción Completa", state="complete")
                    with st.spinner("Generando PDF final..."):
                        output_pdf = self.pdf_processor.rebuild_pdf(self.current_state.state["content"])
                        st.download_button(
                            "Descargar PDF Traducido",
                            output_pdf.tobytes(),
                            f"translated_{self._filename}"
                        )
                    self.current_state.purge_state()
                else:
                    status.update(label="Traducción Parcial", state="error")
                    st.error("No se pudo traducir todo el contenido. Por favor, intente nuevamente.")
                    self.current_state.update_position(0)
                    # self._render_comparison_table()

        except Exception as e:
            st.error(f"Error crítico: {str(e)}")
            st.stop()

    def _render_progress(self):
        """Muestra barra de progreso"""
        translated_count = sum(1 for item in self.current_state.state["content"] if item['metadata']['translated'])
        total_items = len(self.current_state.state["content"])
        st.progress(translated_count / total_items)
        st.caption(f"Elementos traducidos: {translated_count}/{total_items}")

    def _render_comparison_table(self):
        """Muestra tabla comparativa"""
        if translated_count := sum(1 for item in self.current_state.state["content"] if item['metadata']['translated']):
            st.subheader("Comparación de Contenido")
            df = pd.DataFrame([{
                "Página": item['metadata']['page'] + 1,
                "Original": item['original'],
                "Traducción": item['translated']
            } for item in self.current_state.state["content"] if
                item['type'] == 'text' and item['metadata']['translated']])

            if not df.empty:
                self._display_paginated_table(df)
            else:
                st.info("No hay contenido traducido para mostrar aún")

    def _display_paginated_table(self, df):
        """Implementa paginación manual para Streamlit"""
        page_size = st.selectbox("Filas por página", [5, 10, 20], index=1)

        # Calcular total de páginas
        total_pages = (len(df) // page_size) + (1 if len(df) % page_size > 0 else 0)

        # Inicializar página actual
        if "page" not in st.query_params:
            st.query_params["page"] = 1

        # Manejar navegación por query params
        query_params = st.query_params["page"]
        current_page = int(query_params)
        current_page = max(1, min(current_page, total_pages))

        # Controles de navegación
        col1, col2, col3 = st.columns([1, 2, 1])
        with col1:
            if st.button("Anterior", disabled=current_page == 1):
                current_page -= 1
        with col3:
            if st.button("Siguiente", disabled=current_page >= total_pages):
                current_page += 1

        # Actualizar parámetros de URL
        st.query_params["page"] = current_page

        # Mostrar datos paginados
        start_idx = (current_page - 1) * page_size
        end_idx = start_idx + page_size

        st.dataframe(
            df.iloc[start_idx:end_idx],
            use_container_width=True,
            hide_index=True,
            column_config={
                "Original": {"width": "45%"},
                "Traducción": {"width": "45%"},
                "Página": {"width": "10%"}
            }
        )

        st.caption(f"Página {current_page} de {total_pages}")


# ---------- Ejecución Principal ----------
if __name__ == "__main__":
    ui = TranslationUI()
    ui.render_interface()
