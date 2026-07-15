"""Text Processing CLI.

CUPID Principles:
- Composable: Each command is independent
- Unix Philosophy: Stdin/Stdout streaming, composable with pipes
- Predictable: Deterministic output for same input
- Idiomatic: Typer + Rich for modern CLI
- Domain-Focused: Text processing domain only
"""

from __future__ import annotations
import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from ..core.chunker import TextChunker, Tokenizer
from ..models.chunk import ChunkResult
from ..models.config import ChunkConfig, EncodingType, SplitStrategy

app = typer.Typer(
    name="pdftranslator-text",
    help="Text processing utilities for chunking, normalization, and analysis",
    add_completion=False,
    rich_markup_mode="rich",
)

console = Console()


@app.command("chunk")
def chunk_text(
    input_file: Optional[Path] = typer.Argument(
        None,
        help="Input file (stdin if not provided)",
        exists=True,
        readable=True,
    ),
    max_tokens: int = typer.Option(
        500,
        "--tokens",
        "-t",
        help="Maximum tokens per chunk",
        min=1,
    ),
    overlap: int = typer.Option(
        50,
        "--overlap",
        "-o",
        help="Overlap tokens between chunks",
        min=0,
    ),
    min_tokens: int = typer.Option(
        50,
        "--min-tokens",
        help="Minimum tokens per chunk",
        min=1,
    ),
    encoding: EncodingType = typer.Option(
        EncodingType.CL100K_BASE,
        "--encoding",
        "-e",
        help="Token encoding",
        case_sensitive=False,
    ),
    strategy: SplitStrategy = typer.Option(
        SplitStrategy.TOKENS,
        "--strategy",
        "-s",
        help="Chunking strategy",
        case_sensitive=False,
    ),
    output: Optional[Path] = typer.Option(
        None,
        "--output",
        "-O",
        help="Output file (stdout if not provided)",
    ),
    format: str = typer.Option(
        "json",
        "--format",
        "-f",
        help="Output format: json, jsonl, text",
        case_sensitive=False,
    ),
    stats: bool = typer.Option(
        False,
        "--stats",
        help="Show chunking statistics",
    ),
):
    """Chunk text into token-bounded segments.

    Examples:
        echo "Hello world" | pdftranslator-text chunk -t 100
        pdftranslator-text chunk document.txt -t 512 -o 64 -f jsonl > chunks.jsonl
        cat input.txt | pdftranslator-text chunk -s sentences --stats
    """
    # Read input
    if input_file:
        text = input_file.read_text(encoding="utf-8")
    else:
        text = sys.stdin.read()

    if not text.strip():
        console.print("[yellow]No input text provided[/yellow]")
        raise typer.Exit(0)

    # Configure chunker
    config = ChunkConfig(
        max_tokens=max_tokens,
        overlap_tokens=overlap,
        min_tokens=min_tokens,
        encoding=encoding,
        split_strategy=strategy,
    )
    chunker = TextChunker(config)

    # Chunk the text
    result: ChunkResult = chunker.chunk(text)

    # Output
    if format == "json":
        output_data = _serialize_json(result)
    elif format == "jsonl":
        output_data = _serialize_jsonl(result)
    elif format == "text":
        output_data = _serialize_text(result)
    else:
        console.print(f"[red]Unknown format: {format}[/red]")
        raise typer.Exit(1)

    if output:
        output.write_text(output_data, encoding="utf-8")
    else:
        console.print(output_data, end="")

    # Statistics
    if stats:
        _print_stats(result)


@app.command("tokenize")
def tokenize_text(
    input_file: Optional[Path] = typer.Argument(
        None, exists=True, readable=True, help="Input file (stdin if not provided)"
    ),
    encoding: EncodingType = typer.Option(
        EncodingType.CL100K_BASE, "--encoding", "-e", case_sensitive=False
    ),
    count_only: bool = typer.Option(
        False, "--count-only", "-c", help="Only output token count"
    ),
):
    """Tokenize text and show tokens or count.

    Examples:
        echo "Hello world" | pdftranslator-text tokenize
        pdftranslator-text tokenize document.txt --count-only
    """
    if input_file:
        text = input_file.read_text(encoding="utf-8")
    else:
        text = sys.stdin.read()

    tokenizer = Tokenizer.get(encoding)
    tokens = tokenizer.encode_ordinary(text)

    if count_only:
        console.print(len(tokens))
    else:
        console.print(f"Tokens: {len(tokens)}")
        console.print(f"Characters: {len(text)}")
        console.print("Token IDs:", " ".join(str(t) for t in tokens[:50]) + ("..." if len(tokens) > 50 else ""))


@app.command("analyze")
def analyze_text(
    input_file: Optional[Path] = typer.Argument(
        None, exists=True, readable=True, help="Input file (stdin if not provided)"
    ),
    encoding: EncodingType = typer.Option(
        EncodingType.CL100K_BASE, "--encoding", "-e", case_sensitive=False
    ),
):
    """Analyze text statistics.

    Examples:
        cat document.txt | pdftranslator-text analyze
    """
    if input_file:
        text = input_file.read_text(encoding="utf-8")
    else:
        text = sys.stdin.read()

    tokenizer = Tokenizer.get(encoding)
    tokens = tokenizer.encode_ordinary(text)

    lines = text.split("\n")
    words = text.split()
    chars = len(text)

    table = Table(title="Text Analysis")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("Characters", f"{chars:,}")
    table.add_row("Words", f"{len(words):,}")
    table.add_row("Lines", f"{len(lines):,}")
    table.add_row("Tokens", f"{len(tokens):,}")
    table.add_row("Chars/token", f"{chars/len(tokens):.2f}" if tokens else "N/A")
    table.add_row("Tokens/word", f"{len(tokens)/len(words):.2f}" if words else "N/A")

    # Estimate for common models
    table.add_section()
    table.add_row("GPT-4 (8k) fit", f"{(8192/len(tokens))*100:.1f}%" if tokens else "N/A")
    table.add_row("GPT-4 (32k) fit", f"{(32768/len(tokens))*100:.1f}%" if tokens else "N/A")
    table.add_row("Embedding (8k) fit", f"{(8191/len(tokens))*100:.1f}%" if tokens else "N/A")

    console.print(table)


@app.command("config")
def show_config(
    max_tokens: int = typer.Option(500, "--tokens", "-t"),
    overlap: int = typer.Option(50, "--overlap", "-o"),
    min_tokens: int = typer.Option(50, "--min-tokens"),
    encoding: EncodingType = typer.Option(EncodingType.CL100K_BASE, "--encoding", "-e"),
    strategy: SplitStrategy = typer.Option(SplitStrategy.TOKENS, "--strategy", "-s"),
):
    """Show resolved configuration."""
    config = ChunkConfig(
        max_tokens=max_tokens,
        overlap_tokens=overlap,
        min_tokens=min_tokens,
        encoding=encoding,
        split_strategy=strategy,
    )

    console.print("[bold]Resolved Configuration[/bold]")
    for key, value in config.to_dict().items():
        console.print(f"  {key}: {value}")


def _serialize_json(result: ChunkResult) -> str:
    import json
    return json.dumps(
        {
            "chunks": [
                {
                    "text": c.text,
                    "token_count": c.token_count,
                    "sequence_number": c.sequence_number,
                    "char_start": c.char_start,
                    "char_end": c.char_end,
                    "uuid": str(c.uuid),
                    "metadata": c.metadata,
                }
                for c in result.chunks
            ],
            "total_chunks": result.total_chunks,
            "total_tokens": result.total_tokens,
            "total_chars": result.total_chars,
            "config": result.config.to_dict(),
        },
        ensure_ascii=False,
        indent=2,
    ) + "\n"


def _serialize_jsonl(result: ChunkResult) -> str:
    import json
    lines = []
    for c in result.chunks:
        lines.append(
            json.dumps(
                {
                    "text": c.text,
                    "token_count": c.token_count,
                    "sequence_number": c.sequence_number,
                    "char_start": c.char_start,
                    "char_end": c.char_end,
                    "uuid": str(c.uuid),
                    "metadata": c.metadata,
                },
                ensure_ascii=False,
            )
        )
    return "\n".join(lines) + "\n"


def _serialize_text(result: ChunkResult) -> str:
    lines = []
    for c in result.chunks:
        lines.append(f"--- Chunk {c.sequence_number} ({c.token_count} tokens) ---")
        lines.append(c.text)
        lines.append("")
    return "\n".join(lines)


def _print_stats(result: ChunkResult) -> None:
    table = Table(title="Chunking Statistics")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("Total chunks", str(result.total_chunks))
    table.add_row("Total tokens", f"{result.total_tokens:,}")
    table.add_row("Total characters", f"{result.total_chars:,}")
    table.add_row("Avg tokens/chunk", f"{result.total_tokens/result.total_chunks:.1f}" if result.total_chunks else "0")
    table.add_row("Avg chars/chunk", f"{result.total_chars/result.total_chunks:.1f}" if result.total_chunks else "0")
    table.add_row("Max tokens/chunk", str(result.config.max_tokens))
    table.add_row("Overlap tokens", str(result.config.overlap_tokens))

    console.print()
    console.print(table)


if __name__ == "__main__":
    app()