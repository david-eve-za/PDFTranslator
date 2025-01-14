# Clase OutputGenerator
import io
import pathlib

import fitz
from tqdm import tqdm


class OutputGenerator:
    def __init__(self):
        """
        Initialize the OutputGenerator class.

        This class is used to generate the output PDF file from the translated content.
        """
        self.font_path = pathlib.Path(__file__).parent / "fonts/Roboto-Bold.ttf"
        """
        The path to the font file used for rendering text in the output PDF file.
        """

    def reconstruct_pdf(self, source_content, translated_content, output_path):
        """
        Reconstructs the output PDF by taking the translated content and replacing the text
        in the original PDF with the translated content.

        Args:
            source_content (str): The path to the original PDF file
            translated_content (list): The list of translated content
            output_path (str): The path to the output PDF file
        """
        doc = fitz.open()
        with fitz.open(source_content) as original_content:
            for page_content in tqdm(translated_content, desc="Processing Translated content", unit="page",
                                     leave=False):
                page = doc.new_page()
                if "text" in page_content:
                    # Replace some special characters that are not supported by the PDF
                    # rendering
                    page_content["text"] = (
                        page_content["text"]
                        .replace("”", "\"")
                        .replace("“", "\"")
                        .replace("’", "'")
                        .replace("‘", "'")
                        .replace("—", "-")
                        .replace("\n", "<br>")
                    )
                    # Insert the translated text into the page
                    page.insert_htmlbox(
                        page.mediabox + (36, 36, -36, -36),
                        page_content["text"],
                        archive=self.font_path
                    )
                elif "images" in page_content:
                    # Extract the image from the original PDF
                    xref = page_content["images"][0]
                    image = original_content.extract_image(xref)
                    image_stream = self.compress_image(image)
                    # Insert the image into the page
                    page.insert_image(page.mediabox, stream=image_stream)
        # Save the output PDF
        doc.save(output_path, deflate=True, deflate_images=True)

    def compress_image(self, image):
        """
        Compresses the given image using PIL to reduce the size of the output PDF.

        Args:
            image (dict): The image information extracted from the PDF

        Returns:
            bytes: The compressed image stream
        """
        pixmap = fitz.Pixmap(image["image"])
        buffer = io.BytesIO()
        img = pixmap.pil_save(buffer, "JPEG", quality=20)
        buffer.seek(0)
        return buffer.getvalue()
