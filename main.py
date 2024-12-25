import os
from typing import Optional

import fitz  # PyMuPDF
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
from langchain.memory import ConversationBufferWindowMemory
from langchain_ollama import OllamaLLM
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from io import BytesIO


class PDFTranslator:
    def __init__(
        self,
        source_language: str,
        target_language: str,
        model_name: Optional[str] = "gemma2:27b",
        memory_window_size: int = 5
    ) -> None:
        """
        Initialize the translation system with the source language, target language, and language model.

        :param source_language: The original language of the text (e.g., 'English').
        :param target_language: The language to translate the text to (e.g., 'Spanish').
        :param model_name: The name of the language model (default: 'gemma2:27b').
        :param memory_window_size: The number of previous interactions to remember in the conversation history.
        """
        self.source_language = source_language
        self.target_language = target_language

        # Check that the specified memory window size is valid
        if memory_window_size < 1:
            raise ValueError(f"Invalid memory window size: {memory_window_size}")

        # Configure LangChain with contextual memory
        self.memory = ConversationBufferWindowMemory(
            memory_key="context",
            input_key="text",
            k=memory_window_size
        )
        self.prompt = PromptTemplate(
            input_variables=["text", "source_language", "target_language", "context"],
            template=(
                "You are translating a document. Maintain the context of the previous text.\n\n"
                "Previous context:\n{context}\n\n"
                "Translate the following text from {source_language} to {target_language}:\n\n"
                "{text}\n\n"
                "Provide the translated text only."
            ),
        )
        self.llm_chain = LLMChain(
            llm=OllamaLLM(model=model_name, temperature=0.1),
            prompt=self.prompt,
            memory=self.memory,
            verbose=True
        )

    def translate_text(self, text: str) -> str:
        """
        Translate the given text from the source language to the target language.

        :param text: The text to translate.
        :return: The translated text.
        """
        # Check that the text is not empty
        if not text.strip():
            raise ValueError("Text to translate cannot be empty")

        # Create a new input for the LLM chain
        input = {
            "text": text,
            "source_language": self.source_language,
            "target_language": self.target_language
        }

        # Run the LLM chain to generate the translation
        output = self.llm_chain(input)

        # Extract the translated text from the output
        translated_text = output["text"]

        return translated_text

    def translate_pdf(self, input_pdf_path, output_pdf_path):
        """
        Traduce el contenido de un PDF y guarda un nuevo PDF con la traducción.

        :param input_pdf_path: Ruta del PDF original.
        :param output_pdf_path: Ruta donde se guardará el PDF traducido.
        """
        doc = fitz.open(input_pdf_path)

        # Crear un nuevo documento PDF
        translated_pdf_buffer = BytesIO()
        c = canvas.Canvas(translated_pdf_buffer, pagesize=letter)

        for page_index in range(len(doc)):
            page = doc[page_index]
            blocks = page.get_text("dict")["blocks"]

            # Ajustar posición inicial
            y_position = 750  # Margen superior inicial
            x_margin = 50  # Margen izquierdo

            for block in blocks:
                if "lines" in block:
                    for line in block["lines"]:
                        for span in line["spans"]:
                            original_text = span["text"]

                            # Traducir texto con contexto acumulado
                            translated_text = self.translate_text(original_text)

                            # Verificar espacio disponible en la página
                            if y_position < 50:
                                c.showPage()
                                y_position = 750

                            # Dibujar texto traducido en el nuevo PDF
                            c.drawString(x_margin, y_position, translated_text)
                            y_position -= 12  # Ajustar altura del texto

                elif "image" in block:
                    xref = block["image"]
                    pix = fitz.Pixmap(xref)

                    # Convertir imagen a formato compatible con ReportLab
                    if pix.n > 4:
                        pix = fitz.Pixmap(fitz.csRGB, pix)

                    img_buffer = BytesIO(pix.tobytes("png"))
                    img_width, img_height = pix.width, pix.height

                    # Escalar imagen para ajustarla al tamaño de la página
                    scale = min(500 / img_width, 700 / img_height)
                    img_width *= scale
                    img_height *= scale

                    # Verificar espacio en la página para imágenes
                    if y_position < img_height + 50:
                        c.showPage()
                        y_position = 750

                    # Dibujar la imagen en el nuevo PDF
                    c.drawImage(
                        ImageReader(img_buffer),
                        x_margin,
                        y_position - img_height,
                        width=img_width,
                        height=img_height,
                    )
                    y_position -= img_height + 20

            # Crear nueva página si no es la última
            if page_index < len(doc) - 1:
                c.showPage()

        # Finalizar el nuevo PDF
        c.save()

        # Guardar el PDF traducido
        with open(output_pdf_path, "wb") as f:
            f.write(translated_pdf_buffer.getvalue())

        doc.close()

    def translate_pdfs_in_directory(self, directory_path):
        """
        Busca y traduce todos los archivos PDF en un directorio y sus subdirectorios.

        :param directory_path: Ruta del directorio principal.
        """
        pdf_files = []

        # Recorrer el directorio y las subcarpetas
        for root, _, files in os.walk(directory_path):
            for file in files:
                if file.endswith(".pdf"):
                    pdf_files.append(os.path.join(root, file))

        # Ordenar la lista de archivos PDF alfabéticamente
        pdf_files.sort()

        # Traducir cada PDF
        for pdf_path in pdf_files:
            directory, filename = os.path.split(pdf_path)
            translated_filename = f"translated_{filename}"
            translated_path = os.path.join(directory, translated_filename)

            print(f"Traduciendo: {pdf_path} -> {translated_path}")
            self.translate_pdf(pdf_path, translated_path)


# Ejemplo de uso
if __name__ == "__main__":
    # Idiomas
    source_language = "English"
    target_language = "Spanish"

    # Ruta del directorio
    directory = "/Volumes/Elements/Peliculas/.Hide/Thinks/NVL/ENG/A Late-Start Tamer\'s Laid-Back Life/"

    # Crear una instancia de PDFTranslator
    translator = PDFTranslator(
        source_language=source_language,
        target_language=target_language,
        memory_window_size=10  # Ajusta el tamaño de la memoria según sea necesario
    )

    # Traducir el PDF
    translator.translate_pdfs_in_directory(directory)
