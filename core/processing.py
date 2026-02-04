from itertools import islice
from pathlib import Path
from rich import print as pr
from core.ctags_extraction import extract_ctags_for_source_files
from core.exceptions import FileReadError
from core.file_io import FileReader, FilesystemFileReader
from core.models import (
    CategoryProcessedFiles,
    FileCategory,
    FileMetadata,
    ProcessedFile,
)
from core.tokens import (
    PooledTokenBudget,
    TokenBudget,
    TokenCounter,
    TiktokenCounter,
    TokenLimits,
)
from ui.progress_display import ProgressDisplay, RichProgressDisplay


def process_files(
    root: Path,
    files_by_category: dict[FileCategory, list[FileMetadata]],
    counter: TokenCounter | None = None,
    token_budget: TokenBudget | None = None,
) -> dict[FileCategory, CategoryProcessedFiles]:
    """
    Process files by category with token budget management.

    Processes files in a predefined order (CONTEXT, MANIFEST, SIGNAL, SOURCE),
    applying appropriate extraction logic for each category. Files are sorted by
    significance score before processing, and token budgets are enforced to
    prevent exceeding limits.

    Args:
        root: Root directory of the project, used to resolve relative file paths.
        files_by_category: Dictionary mapping file categories to lists of file
            metadata. Files should be pre-categorized before calling this function.
        counter: Optional token counter instance. If None, creates a TiktokenCounter
            with default model "gpt-4o".
        token_budget: Optional token budget manager. If None, creates a PooledTokenBudget
            with default TokenLimits.

    Returns:
        Dictionary mapping file categories to CategoryProcessedFiles objects
        containing the successfully processed files for each category.
    """
    if counter is None:
        counter = TiktokenCounter("gpt-4o")
    if token_budget is None:
        token_budget = PooledTokenBudget(TokenLimits())

    processing_order = [
        FileCategory.CONTEXT,
        FileCategory.MANIFEST,
        FileCategory.SIGNAL,
        FileCategory.SOURCE,
    ]

    status_results: dict[FileCategory, CategoryProcessedFiles] = {}

    for category in processing_order:
        files_in_category = files_by_category[category]
        if not files_in_category:
            continue

        files_in_category.sort(
            key=lambda file_meta: (file_meta.score, -file_meta.depth), reverse=True
        )

        status = CategoryProcessedFiles(category)

        if category == FileCategory.SOURCE:
            extract_ctags_for_source_files(
                root,
                files_in_category,
                counter,
                token_budget,
                status,
            )
        else:
            process_readable_files_for_category(
                root,
                files_in_category,
                counter,
                token_budget,
                status,
            )

        status_results[category] = status

    return status_results


def process_readable_files_for_category(
    root: Path,
    files: list[FileMetadata],
    counter: TokenCounter,
    token_budget: TokenBudget,
    status: CategoryProcessedFiles,
    progress_display: ProgressDisplay | None = None,
    file_reader: FileReader | None = None,
) -> None:

    category = status.category

    category_to_text = {
        FileCategory.CONTEXT: {
            "description": "📖 Establishing project context...",
            "name": "context files",
        },
        FileCategory.MANIFEST: {
            "description": "📦 Analyzing manifest & dependency files...",
            "name": "manifest files",
        },
        FileCategory.SIGNAL: {
            "description": "🎯 Identifying high-signal entry points...",
            "name": "high-signal files",
        },
    }
    files_processed = 0

    pr(f"\n[bold magenta]{category_to_text[category]["description"]}[/bold magenta]")

    token_budget.start_category(category)

    reader = file_reader if file_reader is not None else FilesystemFileReader()
    rich_progress_display = (
        progress_display if progress_display is not None else RichProgressDisplay()
    )

    with rich_progress_display as rpd:
        rpd.on_start(f"Reading {category_to_text[category]["name"]}...", None)

        for file_meta in islice(files, None):
            full_path = root / file_meta.file_path
            if not full_path.exists():
                continue

            try:
                content = reader.read_file(full_path)
            except FileReadError as e:
                # Log the error but continue processing other files
                pr(
                    f"[yellow]⚠ Warning:[/yellow] Failed to read file {file_meta.file_path}: {e.message}"
                )
                continue

            token_usage = counter.count(content)
            if token_budget.can_afford(token_usage):
                token_budget.spend(token_usage)
                status.append(
                    ProcessedFile(str(file_meta.file_path), category.value, content)
                )
                files_processed += 1
            else:
                break

        rpd.on_complete(
            f"✅ Read {files_processed} {category_to_text[category]["name"]}.", 100, 100
        )
