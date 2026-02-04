"""
Module for extracting code symbols from source files using ctags.

This module provides functionality to:
- Run ctags on batches of source files to extract code symbols (functions, classes, variables, etc.)
- Parse JSON-formatted ctags output into structured data
- Manage token budgets while processing files to stay within limits
- Format extracted symbols for further processing

The main entry point is `extract_ctags_for_source_files()`, which orchestrates the
extraction process with token budget management and progress tracking. Files are
processed in batches to efficiently handle large codebases while respecting token
budget constraints.
"""

from itertools import islice
from pathlib import Path
from typing import Callable
import json
import subprocess
from rich import print as pr
from adapters.ctags import get_ctags_path
from constants import CTAGS_KINDS
from core.models import (
    CategoryProcessedFiles,
    Ctag,
    FileCategory,
    FileMetadata,
    ProcessedFile,
)
from core.tokens import TokenBudget, TokenCounter
from ui.progress_display import ProgressDisplay, RichProgressDisplay


def extract_ctags_for_source_files(
    root: Path,
    files: list[FileMetadata],
    counter: TokenCounter,
    token_budget: TokenBudget,
    status: CategoryProcessedFiles,
    progress_display: ProgressDisplay | None = None,
) -> None:
    """
    Extract code symbols from source files using ctags with token budget management.

    This function processes source files in batches, running ctags to extract code
    symbols (functions, classes, variables, etc.) and formats them for further
    processing. The extraction respects token budget constraints, stopping when the
    budget is exhausted to prevent exceeding limits.

    The function processes files iteratively in batches, checking token usage for
    each processed file before adding it to the status. If a file would exceed the
    remaining budget, processing stops and the file is not included.

    Args:
        root: Root directory of the project, used to resolve relative file paths.
        files: List of file metadata objects representing source files to process.
        counter: Token counter instance used to calculate token usage for extracted
            symbol content.
        token_budget: Token budget manager that tracks remaining budget and enforces
            limits. The category is started automatically before processing.
        status: CategoryProcessedFiles object that accumulates successfully processed
            files. Files are appended to this object as they are processed.
        progress_display: Optional progress display instance for showing extraction
            progress. If None, uses RichProgressDisplay by default.

    Returns:
        None: This function modifies the status object in place and does not return
            a value.

    Note:
        Files are processed in batches (default batch size: 100) to efficiently
        handle large codebases. Processing stops early if the token budget is
        exhausted or all files have been processed.
    """

    pr("\n[bold magenta]👀  Looking into source files...[/bold magenta]")

    start = 0
    files_processed = 0

    token_budget.start_category(status.category)

    rich_progress_display = (
        progress_display if progress_display is not None else RichProgressDisplay()
    )
    with rich_progress_display as rpd:
        rpd.on_start("Generating code symbols...", None)
        budget_exhausted = False
        list_fully_processed = False

        while True:
            processed_files, start = _run_ctags(root, files, start)

            if not processed_files:
                break

            if start >= len(files):
                list_fully_processed = True

            for file in processed_files:
                token_usage = counter.count(file.content)

                if token_budget.can_afford(token_usage):
                    token_budget.spend(token_usage)
                    status.append(file)
                    files_processed += 1
                else:
                    budget_exhausted = True
                    break

            if budget_exhausted or list_fully_processed:
                break

        rpd.on_complete(
            f"✅ Generated code symbols for {files_processed} files.",
            total=100,
            completed=100,
        )


def _run_ctags(
    root: Path,
    files: list[FileMetadata],
    start: int = 0,
    category: FileCategory = FileCategory.SOURCE,
    ctags_path: Path | None = None,
    limit: int = 100,
    popen_factory: Callable | None = None,
) -> tuple[list[ProcessedFile] | None, int]:
    """
    Run ctags on a batch of source files and parse the output.

    Args:
        root: Root directory of the project
        files: List of file metadata to process
        start: Starting index in the files list
        category: File category (must be SOURCE)
        ctags_path: Optional path to ctags binary. If None, uses get_ctags_path()
        limit: Maximum number of files to process in this batch (default: 100)
        popen_factory: Optional factory function for creating subprocess.Popen.
            If None, uses subprocess.Popen. Useful for testing.

    Returns:
        Tuple of (list of ProcessedFile objects, next start index) or (None, current_index) on error
    """

    if category != FileCategory.SOURCE:
        raise ValueError("Ctags must only be run on source files")

    stop = start + limit
    processed_files: list[ProcessedFile] = []
    current_index = start

    file_paths = [str(root / p.file_path) for p in islice(files, start, stop)]

    if not ctags_path:
        ctags_path = get_ctags_path()

    # Flags:
    # --output-format=json: easier parsing
    # --fields=+n: give us line numbers
    # --filter: run in "interactive" mode (keep process alive)
    cmd = [
        str(ctags_path),
        "--output-format=json",
        "--sort=no",
        "--fields=+n",
        "-f",
        "-",
    ]
    # Append all paths as arguments
    # subprocess handles escaping/quoting automatically
    cmd.extend(file_paths)

    popen = popen_factory if popen_factory else subprocess.Popen
    try:
        with popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            encoding="utf-8",
            errors="replace",  # CRITICAL: Don't crash if Ctags outputs weird chars
            bufsize=1,
        ) as process:

            current_file_path = None
            current_file_tags: list[str] = []

            if process.stdout:
                for line in process.stdout:
                    # Empty string from readline() means EOF (stream closed) - exit loop
                    if line == "":
                        return (None, current_index)

                    line = line.strip()
                    # Empty string after strip means blank/whitespace-only line - skip it
                    if not line:
                        continue

                    ctag = _parse_tag_line(line)
                    if not ctag:
                        continue

                    if ctag.path != current_file_path:
                        if current_file_path:
                            processed_files.append(
                                ProcessedFile(
                                    _get_rel_path_str_from_str(root, current_file_path),
                                    category.value,
                                    "\n".join(current_file_tags),
                                )
                            )
                        current_file_path = ctag.path
                        current_file_tags = []
                        current_index += 1

                    current_file_tags.append(format_tag(ctag.kind, ctag.name))

            if current_file_path:
                processed_files.append(
                    ProcessedFile(
                        _get_rel_path_str_from_str(root, current_file_path),
                        category.value,
                        "\n".join(current_file_tags),
                    )
                )

    except (OSError, subprocess.SubprocessError):
        return (None, current_index)

    return (processed_files, current_index)


def _parse_tag_line(line: str) -> Ctag | None:
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


def _get_rel_path_str_from_str(root: Path, full_path_str: str) -> str:
    full_path = Path(full_path_str)
    relative_str = str(full_path.relative_to(root))
    return relative_str


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
