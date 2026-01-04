"""
Code symbol extraction and payload generation module.

This module orchestrates the final assembly of the Sential payload by reading
context files in full and extracting code symbols via Universal Ctags. It generates
a JSONL file containing both full file contents (for context) and symbol metadata
(for code structure understanding).
"""

import io
import subprocess
import tempfile
from pathlib import Path
import typer
from rich import print as pr
from constants import (
    SupportedLanguage,
)
from core.context_reader import process_context_files

from core.models import InventoryResult
from core.symbol_extractor import (
    build_ctags_command,
    process_ctags_output,
)


def generate_tags_jsonl(
    root_path: Path,
    inventory_result: InventoryResult,
    language: SupportedLanguage,
) -> Path:
    """
    Generates the final JSONL payload containing file contents and code symbols.

    This function acts as the final assembly line. It performs two main phases:
    1.  **Context Phase:** Reads the full content of "Context Files" (identified in the
        inventory result). It prioritizes specific files (like manifests) and writes
        them to the output first.
    2.  **Tags Phase:** Extracts symbols from the "Language Files" listed in the inventory
        using Universal Ctags and writes symbol records to the output.

    Args:
        root_path (Path): The absolute root path of the repository.
        inventory_result (InventoryResult): An object containing paths to source and
            context inventory files, along with statistics about file counts.
        language (SupportedLanguage): The target language (used to prioritize specific
            manifests).

    Returns:
        Path: The file path to the generated `sential_payload.jsonl` in the system temp directory.
    """

    source_path = inventory_result.source_inventory_path
    context_path = inventory_result.context_inventory_path
    lang_file_count = inventory_result.stats.language_files
    ctx_file_count = inventory_result.stats.context_files

    output_path = Path(tempfile.gettempdir()) / "sential_payload.jsonl"

    pr("\n[bold magenta]📄  Reading context files...[/bold magenta]")

    success = False

    try:

        with open(output_path, "w", encoding="utf-8") as out_f:
            # --- PHASE 1: CONTEXT FILES (Full Content) ---
            process_context_files(
                root_path, context_path, out_f, language, ctx_file_count
            )
            # --- PHASE 2: PROCESS LANG FILES CTAGS ---
            extract_symbols(root_path, source_path, out_f, lang_file_count)
        success = True

    except KeyboardInterrupt as exc:
        pr("\n[yellow]Interrupted by user[/yellow]")
        raise typer.Exit() from exc
    except Exception as e:
        pr(f"[bold red]Error: {e}[/bold red]")
        raise typer.Exit()

    finally:
        # Clean up output file only if generation failed
        # Temp inventory files (source_path, context_path) are cleaned up by FileInventoryWriter context manager
        if not success:
            output_path.unlink(missing_ok=True)

    return output_path


def extract_symbols(
    base_path: Path,
    inventory_path: Path,
    out_f: io.TextIOWrapper,
    lang_file_count: int,
) -> None:
    """
    Executes Universal Ctags on the provided inventory of files and streams the output to JSONL.

    This function streams file paths from `inventory_path` into the `ctags` subprocess via stdin.
    It parses the JSON output from ctags, aggregates symbols (tags) by file path, and writes
    a compressed record (path + list of tags) to the open output file handle `out_f`.

    Args:
        base_path (Path): The working directory for the ctags subprocess.
        inventory_path (Path): Path to the temporary file containing the list of source files to scan.
        out_f (io.TextIOWrapper): An open file handle (write mode) where the JSONL records will be written.
        lang_file_count (int): The total number of files to process, used for the progress bar.
    """

    pr("\n[bold magenta]🏷️  Extracting code symbols...[/bold magenta]")

    cmd = build_ctags_command()

    with open(inventory_path, "r", encoding="utf-8") as in_f:
        with subprocess.Popen(
            cmd,
            cwd=base_path,
            stdin=in_f,  # Feed the file list via stdin
            stdout=subprocess.PIPE,  # Catch output via pipe
            stderr=subprocess.DEVNULL,
            text=True,
            bufsize=1,
        ) as process:
            process_ctags_output(process, out_f, lang_file_count)
