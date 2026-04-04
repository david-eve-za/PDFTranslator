"""
Document Chapter Splitter V2 - Using Docling for structure extraction.

Divide un documento (PDF, DOCX) en secciones narrativas estructuradas:
Prologue, Chapter 1..N, Epilogue usando Docling para extracción de estructura.

Uso:
    python document_chapter_splitter_v2.py mi_novela.pdf
    python document_chapter_splitter_v2.py mi_novela.docx --output ./salida
"""

import argparse
import json
import logging
import re
from pathlib import Path

from config.settings import Settings
from infrastructure.llm.protocol import LLMClient
from infrastructure.llm.nvidia import NvidiaLLM
from infrastructure.document.docling_extractor import DoclingExtractor
from infrastructure.document.section_grouper import SectionGrouper

logger = logging.getLogger(__name__)

SECTION_CLASSIFICATION_PROMPT = """
Eres un clasificador de secciones de libros narrativos.

Tu tarea es clasificar una sección como:
- "prologue": Prólogo o prefacio del autor
- "chapter": Capítulo numerado o titulado
- "epilogue": Epílogo o postfacio
- "other": Índice, agradecimientos, derechos, publicidad, etc.

INPUT:
Título: {title}
Primeras 300 caracteres del contenido:
{content_preview}

Responde SOLO con JSON válido:
{{"type": "prologue"|"chapter"|"epilogue"|"other", "number": <int|null>}}

Ejemplos:
Input: "Capítulo 5: La batalla" → {{"type": "chapter", "number": 5}}
Input: "Prólogo" → {{"type": "prologue", "number": null}}
Input: "Índice" → {{"type": "other", "number": null}}
""".strip()


class SectionClassifier:
    """Classify document sections using LLM."""

    def __init__(self, llm: LLMClient):
        """
        Initialize classifier.

        Args:
            llm: LLM client with call_model method.
        """
        self.llm = llm

    def classify(self, title: str, content_preview: str) -> dict:
        """
        Classify a section.

        Args:
            title: Section title.
            content_preview: First 300 chars of content.

        Returns:
            Dict with 'type' and 'number' keys.
        """
        return classify_section_with_llm(self.llm, title, content_preview)


def classify_section_with_llm(llm, title: str, content_preview: str) -> dict:
    """
    Classify a section using LLM.

    Args:
        llm: LLM client.
        title: Section title.
        content_preview: First 300 chars of content.

    Returns:
        Dict with 'type' and 'number' keys.

    Raises:
        ValueError: If LLM returns invalid JSON.
    """
    prompt = SECTION_CLASSIFICATION_PROMPT.format(
        title=title, content_preview=content_preview[:300]
    )

    raw = llm.call_model(prompt)

    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)

    try:
        result = json.loads(raw)
        if not isinstance(result, dict):
            raise ValueError(f"Expected dict, got {type(result)}")
        if "type" not in result:
            raise ValueError("Missing 'type' key in response")
        return result
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse LLM response: {raw[:200]}")
        raise ValueError(f"Invalid JSON from LLM: {e}") from e


def split_document_v2(
    filepath: str,
    output_dir: str = "./output",
    llm: LLMClient | None = None,
) -> None:
    """
    Split document using Docling extraction.

    Args:
        filepath: Path to document.
        output_dir: Output directory for sections.
        llm: LLM client for classification. If None, uses NvidiaLLM.

    Raises:
        FileNotFoundError: If filepath does not exist.
    """
    file_path = Path(filepath)
    if not file_path.exists():
        raise FileNotFoundError(f"Document not found: {filepath}")

    settings = Settings.get()
    if llm is None:
        llm = NvidiaLLM(settings)
    extractor = DoclingExtractor(settings.document)
    grouper = SectionGrouper()
    classifier = SectionClassifier(llm)

    print(f"\n{'=' * 60}")
    print(f"Procesando: {filepath}")
    print(f"{'=' * 60}")

    print("\n[1/4] Extrayendo estructura con Docling...")
    doc = extractor.extract(filepath)
    print(f"  Documento extraído: {len(doc.pages)} páginas")

    print("\n[2/4] Agrupando por secciones...")
    sections = grouper.group_by_sections(doc)
    print(f"  {len(sections)} secciones detectadas")

    print("\n[3/4] Clasificando secciones con LLM...")
    narrative_sections = []
    for i, section in enumerate(sections):
        print(
            f"  Sección {i + 1}/{len(sections)}: '{section['title'][:40]}...'", end=" "
        )

        classification = classifier.classify(section["title"], section["content"])
        section["type"] = classification["type"]
        section["number"] = classification.get("number")

        if section["type"] != "other":
            narrative_sections.append(section)
            print(
                f"→ {section['type'].upper()}"
                + (f" #{section['number']}" if section["number"] else "")
            )
        else:
            print("→ (descartado)")

    print(f"\n[4/4] Exportando a '{output_dir}'...")
    export_sections_v2(narrative_sections, output_dir)

    print(f"\n{'=' * 60}")
    print(f"Listo. {len(narrative_sections)} secciones narrativas en '{output_dir}'")
    print(f"{'=' * 60}\n")


def export_sections_v2(sections: list[dict], output_dir: str) -> None:
    """
    Export sections to separate files.

    Args:
        sections: List of section dicts.
        output_dir: Output directory.
    """
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    for i, section in enumerate(sections):
        stype = section.get("type", "section")
        number = section.get("number")
        title = section.get("title", "")

        if stype == "prologue":
            filename = "00_prologue.txt"
        elif stype == "epilogue":
            filename = f"{len(sections):02d}_epilogue.txt"
        elif stype == "chapter":
            num = number or (i + 1)
            safe_title = re.sub(r"[^\w\s-]", "", title)[:40].strip().replace(" ", "_")
            filename = f"{num:02d}_chapter_{safe_title}.txt"
        else:
            filename = f"{i:02d}_{stype}.txt"

        filepath = out / filename
        filepath.write_text(section.get("content", ""), encoding="utf-8")
        print(f"  Guardado: {filename} ({len(section.get('content', ''))} chars)")

    summary = [{k: v for k, v in s.items() if k != "content"} for s in sections]
    (out / "_sections_map.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Divide documento en secciones usando Docling."
    )
    parser.add_argument("filepath", help="Ruta al documento (PDF, DOCX)")
    parser.add_argument(
        "--output",
        "-o",
        default="./output",
        help="Directorio de salida (default: ./output)",
    )
    args = parser.parse_args()

    split_document_v2(args.filepath, args.output)
