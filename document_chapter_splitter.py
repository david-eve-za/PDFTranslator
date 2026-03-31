"""
document_chapter_splitter.py

Divide un documento (PDF, DOCX, TXT, MD) en secciones estructuradas:
Prologue, Chapter 1..N, Epilogue y descarta todo el resto
(páginas de derechos, índices, agradecimientos, etc.)

Dependencias:
    pip install pymupdf python-docx nltk

Uso:
    python document_chapter_splitter.py mi_novela.pdf
    python document_chapter_splitter.py mi_novela.docx --output ./salida
"""

import argparse
import json
import logging
import re
from pathlib import Path

from config.settings import Settings
from infrastructure.llm.nvidia import NvidiaLLM
from llm.base_llm import BaseLLM

logger = logging.getLogger(__name__)

# ─── NLTK DATA VALIDATION ──────────────────────────────────────────────────────

_NLTK_DATA_DOWNLOADED = False


def ensure_nltk_data():
    """
    Ensures that required NLTK data packages are downloaded.

    Downloads 'punkt' and 'punkt_tab' if not found.
    These are required for NLTKTextSplitter to work correctly.
    """
    global _NLTK_DATA_DOWNLOADED
    if _NLTK_DATA_DOWNLOADED:
        return

    import nltk

    required_packages = ["punkt", "punkt_tab"]

    for package in required_packages:
        try:
            nltk.data.find(f"tokenizers/{package}")
            logger.debug(f"NLTK '{package}' found.")
        except LookupError:
            logger.info(f"NLTK '{package}' not found. Downloading...")
            try:
                nltk.download(package, quiet=True)
                logger.info(f"NLTK '{package}' downloaded successfully.")
            except Exception as e:
                logger.error(f"Failed to download NLTK '{package}': {e}")
                raise RuntimeError(
                    f"Failed to download required NLTK data package '{package}'. "
                    f"Please install it manually: python -m nltk.downloader {package}"
                ) from e

    _NLTK_DATA_DOWNLOADED = True


# ─── CONFIGURACIÓN ─────────────────────────────────────────────────────────────

MAX_CHUNK_TOKENS = 6_000  # Tokens por chunk enviado al LLM

# ─── ETAPA 1: EXTRACCIÓN DE TEXTO ──────────────────────────────────────────────


def extract_text(filepath: str) -> str:
    """
    Lee el archivo según su extensión y devuelve el texto crudo completo.
    Soporta: .pdf, .docx, .txt, .md
    """
    path = Path(filepath)
    ext = path.suffix.lower()

    if ext == ".pdf":
        import fitz  # PyMuPDF

        doc = fitz.open(filepath)
        pages = [page.get_text("text") for page in doc]
        return "\n\n[PAGE_BREAK]\n\n".join(pages)

    elif ext == ".docx":
        from docx import Document

        doc = Document(filepath)
        paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
        return "\n\n".join(paragraphs)

    elif ext in (".txt", ".md"):
        return path.read_text(encoding="utf-8")

    else:
        raise ValueError(f"Formato no soportado: {ext}")


# ─── ETAPA 2: ANÁLISIS CON LLM ─────────────────────────────────────────────────

SYSTEM_PROMPT = """
Eres un analizador de documentos narrativos (novelas, libros).
Tu única tarea es identificar secciones estructurales: Prólogo, Capítulos y Epílogo.

REGLAS ESTRICTAS:
1. Responde SOLO con un array JSON válido. Sin texto antes ni después.
2. Cada elemento del array es un objeto con:
   - "type": uno de ["prologue", "chapter", "epilogue", "other"]
   - "title": el título exacto tal como aparece en el texto (puede ser null)
   - "number": número de capítulo si aplica (null para los demás tipos)
   - "start_marker": las primeras 80 caracteres exactas que inician la sección
   - "end_marker": las últimas 80 caracteres exactas que terminan la sección
3. Si un fragmento no pertenece a ninguna sección narrativa (índice,
   agradecimientos, derechos de autor, publicidad), usa type="other".
4. Si el fragmento está cortado a la mitad de una sección, devuelve lo que puedas
   identificar y marca end_marker como null.

Ejemplo de respuesta válida:
[
  {"type": "prologue", "title": "Prólogo", "number": null,
   "start_marker": "Hace mucho tiempo, en una tierra lejana...",
   "end_marker": "...y así comenzó todo."},
  {"type": "chapter", "title": "El comienzo", "number": 1,
   "start_marker": "Capítulo 1\\nEl sol se alzaba sobre las montañas...",
   "end_marker": "...cerró los ojos por última vez esa noche."},
  {"type": "other", "title": null, "number": null,
   "start_marker": "Derechos de autor © 2024...",
   "end_marker": "...Todos los derechos reservados."}
]
""".strip()


def analyze_chunk_with_llm(
    client: BaseLLM,
    chunk: str,
    chunk_index: int,
    total_chunks: int,
) -> list[dict]:
    """
    Envía un chunk al LLM y recibe la lista de secciones detectadas en él.

    El contexto (chunk_index / total_chunks) ayuda al modelo a entender
    si está viendo el principio, el medio o el final del libro.
    """
    prompt = f"""{SYSTEM_PROMPT}

Analiza este fragmento del documento (parte {chunk_index + 1} de {total_chunks}).
Identifica todas las secciones narrativas presentes.

--- INICIO DEL FRAGMENTO ---
{chunk}
--- FIN DEL FRAGMENTO ---
""".strip()

    raw = client.call_model(prompt)

    # Limpieza defensiva: a veces el LLM envuelve en ```json ... ```
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)

    try:
        sections = json.loads(raw)
        if isinstance(sections, dict):
            sections = [sections]
        return sections
    except json.JSONDecodeError as e:
        print(f" [!] Error parsing JSON en chunk {chunk_index}: {e}")
        print(f" Raw: {raw[:200]}...")
        return []


# ─── ETAPA 3: PARSEO, VALIDACIÓN Y MERGE ───────────────────────────────────────


def merge_sections(
    all_sections: list[list[dict]],
    full_text: str,
) -> list[dict]:
    """
    Une los resultados de todos los chunks en una lista ordenada y coherente.

    Desafíos que resuelve:
    - Un capítulo puede aparecer detectado en múltiples chunks (inicio en uno,
      fin en el siguiente). Los fusionamos por número/título.
    - Limpiamos los duplicados.
    - Extraemos el texto real usando los marcadores.
    """
    flat: list[dict] = []
    for chunk_sections in all_sections:
        flat.extend(chunk_sections)

    # Filtramos los "other" (los descartamos)
    narrative = [s for s in flat if s.get("type") != "other"]

    # Deduplicamos: mismo tipo + mismo número → quedamos con el primero
    seen = set()
    unique = []
    for s in narrative:
        key = (s.get("type"), s.get("number"), s.get("title"))
        if key not in seen:
            seen.add(key)
            unique.append(s)

    # Ordenamos: prologue primero, luego capítulos por número, epilogue al final
    def sort_key(s):
        t = s.get("type", "other")
        if t == "prologue":
            return (0, 0)
        if t == "chapter":
            return (1, s.get("number") or 999)
        if t == "epilogue":
            return (2, 0)
        return (3, 0)

    unique.sort(key=sort_key)

    # Extraemos el texto real para cada sección
    for section in unique:
        start_marker = section.get("start_marker")
        end_marker = section.get("end_marker")

        if start_marker and end_marker:
            start_idx = full_text.find(start_marker)
            end_idx = full_text.find(end_marker)

            if start_idx != -1 and end_idx != -1:
                section["text"] = full_text[start_idx : end_idx + len(end_marker)]
            elif start_idx != -1:
                section["text"] = full_text[start_idx : start_idx + 5000] + "..."
            else:
                section["text"] = "[No se pudo extraer el texto de esta sección]"
        else:
            section["text"] = "[Marcadores insuficientes para extraer texto]"

    return unique


# ─── ETAPA 4: EXPORTACIÓN ──────────────────────────────────────────────────────


def export_sections(sections: list[dict], output_dir: str) -> None:
    """
    Guarda cada sección como un archivo .txt separado en output_dir.
    El resto del documento (type=other) ya fue descartado en el merge.
    """
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    for i, section in enumerate(sections):
        stype = section.get("type", "section")
        number = section.get("number")
        title = section.get("title") or ""

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
        filepath.write_text(section.get("text", ""), encoding="utf-8")
        print(f" Guardado: {filename} ({len(section.get('text', ''))} chars)")

    summary = [{k: v for k, v in s.items() if k != "text"} for s in sections]
    (out / "_sections_map.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"\n Mapa guardado: _sections_map.json")


# ─── ORQUESTADOR PRINCIPAL ─────────────────────────────────────────────────────


def split_document(filepath: str, output_dir: str = "./output") -> None:
    """
    Pipeline completo: extrae → divide en chunks → analiza con LLM →
    fusiona secciones → exporta archivos.
    """
    # Ensure NLTK data is available before processing
    ensure_nltk_data()

    settings = Settings.get()
    client = NvidiaLLM(settings)

    print(f"\n{'=' * 60}")
    print(f"Procesando: {filepath}")
    print(f"{'=' * 60}")

    # Etapa 1: Extracción
    print("\n[1/5] Extrayendo texto...")
    full_text = extract_text(filepath)
    print(f" {len(full_text):,} caracteres extraídos")

    # Etapa 2: Chunking
    print("\n[2/5] Dividiendo en chunks...")
    chunks = client.split_into_limit(full_text)
    print(f" {len(chunks)} chunks de máx {MAX_CHUNK_TOKENS} tokens")

    # Etapa 3: Análisis con LLM (chunk por chunk)
    print("\n[3/5] Analizando con LLM...")
    all_sections = []
    for idx, chunk in enumerate(chunks):
        print(f" Chunk {idx + 1}/{len(chunks)}...", end=" ", flush=True)
        sections = analyze_chunk_with_llm(client, chunk, idx, len(chunks))
        all_sections.append(sections)
        found = [s.get("type") for s in sections if s.get("type") != "other"]
        print(f"encontradas: {found if found else 'ninguna sección narrativa'}")

    # Etapa 4: Merge y validación
    print("\n[4/5] Fusionando y validando secciones...")
    final_sections = merge_sections(all_sections, full_text)
    print(f" {len(final_sections)} secciones narrativas identificadas:")
    for s in final_sections:
        label = f" - [{s['type'].upper()}]"
        if s.get("number"):
            label += f" #{s['number']}"
        if s.get("title"):
            label += f" — {s['title']}"
        print(label)

    # Etapa 5: Exportación
    print(f"\n[5/5] Exportando a '{output_dir}'...")
    export_sections(final_sections, output_dir)

    print(f"\n{'=' * 60}")
    print(f"Listo. {len(final_sections)} archivos generados en '{output_dir}'")
    print(f"{'=' * 60}\n")


# ─── ENTRY POINT ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Divide un documento en secciones narrativas usando un LLM."
    )
    parser.add_argument("filepath", help="Ruta al documento (PDF, DOCX, TXT, MD)")
    parser.add_argument(
        "--output",
        "-o",
        default="./output",
        help="Directorio de salida (default: ./output)",
    )
    args = parser.parse_args()

    split_document(args.filepath, args.output)
