"""
Code symbol extraction module using Universal Ctags.

This module handles the extraction of code symbols (functions, classes, variables, etc.)
from source files using Universal Ctags. It processes the JSON output from ctags,
aggregates symbols by file path, and writes compressed symbol records to the output stream.
"""

import io
import json
import subprocess
from typing import Optional
from adapters.ctags import get_ctags_path
from constants import CTAGS_KINDS
from core.models import Ctag
from ui.progress_callback import RichProgressCallback


def process_ctags_output(
    process: subprocess.Popen,
    out_f: io.TextIOWrapper,
    lang_file_count: int,
) -> None:
    """
    Processes the JSON output stream from a ctags subprocess and writes symbol records.

    This function reads JSON lines from the ctags subprocess stdout, parses each tag,
    groups tags by file path, and writes aggregated symbol records to the output file.
    It maintains progress tracking and updates the progress bar as files are processed.

    Args:
        process (subprocess.Popen): The running ctags subprocess with stdout available.
        out_f (io.TextIOWrapper): An open file handle (write mode) where symbol records
            will be written in JSONL format.
        lang_file_count (int): The total number of language files being processed,
            used for progress bar initialization.
    """
    current_file_path = None
    current_tags: list[str] = []

    # We accumulate the tags for the current file path only
    tag_count = 0

    with RichProgressCallback() as callback:

        callback.on_start(
            f"Parsing symbols from {lang_file_count} files...",
            total=lang_file_count,
        )

        if process.stdout:
            for line in process.stdout:
                ctag = parse_tag_line(line)

                if not ctag:
                    continue

                path = ctag.path
                kind = ctag.kind
                name = ctag.name

                if path != current_file_path:
                    if current_file_path:
                        write_symbol_record(out_f, current_file_path, current_tags)
                        callback.on_update(advance=1)
                    # Reset for new file
                    current_file_path = path
                    current_tags = []

                # Add tag to current buffer
                current_tags.append(format_tag(kind, name))
                tag_count += 1

                # Tick the spinner occasionally
                if tag_count % 10 == 0:
                    callback.on_update(
                        description=f"Extracted {tag_count} symbols...",
                    )

            # Write the last file's tags if any
            if current_file_path:
                write_symbol_record(out_f, current_file_path, current_tags)

        callback.on_complete(
            description=f"✅ Extracted {tag_count} symbols",
            completed=lang_file_count,
        )


def build_ctags_command() -> list[str]:
    """
    Builds the command-line arguments for running Universal Ctags.

    Constructs a ctags command that outputs JSON format, reads file paths from stdin,
    and writes to stdout. The command is configured to include name fields and disable
    sorting for streaming processing.

    Returns:
        list[str]: A list of command-line arguments ready to be passed to subprocess.Popen.
    """
    ctags = str(get_ctags_path())
    return [
        ctags,
        "--output-format=json",
        "--sort=no",
        "--fields=+n",
        "-f",
        "-",
        "-L",
        "-",
    ]


def parse_tag_line(line: str) -> Optional[Ctag]:
    """
    Parses a single JSON line from ctags output into a Ctag object.

    Validates that the tag contains required fields (path, name, kind) and that
    the kind is in the allowed set of CTAGS_KINDS. Returns None for invalid or
    malformed tag lines.

    Args:
        line (str): A single JSON-encoded line from ctags output.

    Returns:
        Optional[Ctag]: A Ctag object if the line is valid, None otherwise.
    """
    try:
        tag = json.loads(line)
        path = tag.get("path")
        kind = tag.get("kind")
        name = tag.get("name")

        if not path or not name or kind not in CTAGS_KINDS:
            return None

        return Ctag(path, kind, name)

    except json.JSONDecodeError:
        return None


def write_symbol_record(
    out_f: io.TextIOWrapper, file_path: str, tags: list[str]
) -> None:
    """
    Writes a symbol record to the output file in JSONL format.

    Creates a JSON record containing the file path and its associated tags,
    then writes it as a single line to the output file.

    Args:
        out_f (io.TextIOWrapper): An open file handle (write mode) where the record
            will be written.
        file_path (str): The relative path of the file containing the symbols.
        tags (list[str]): A list of formatted tag strings (e.g., "function myFunction").
    """
    record = {
        "path": file_path,
        "tags": tags,
    }
    out_f.write(json.dumps(record) + "\n")


def format_tag(kind: str, name: str) -> str:
    """
    Formats a tag kind and name into a standardized string representation.

    Args:
        kind (str): The tag kind (e.g., "function", "class", "variable").
        name (str): The name of the symbol.

    Returns:
        str: A formatted string combining kind and name (e.g., "function myFunction").
    """
    return f"{kind} {name}"
