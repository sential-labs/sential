"""
File discovery and inventory generation module.

This module implements the "Language Sieve" pipeline that scans Git repositories,
identifies modules based on manifest files, and classifies files into language
files (source code) and context files (documentation, configs). It generates
temporary inventory files that are used by downstream processing stages.
"""

from enum import Enum
import tempfile
from pathlib import Path
from typing import Generator
from rich import print as pr
from adapters.git import GitClient
from constants import LANGUAGES_HEURISTICS, UNIVERSAL_CONTEXT_FILES
from core.models import InventoryResult, InventoryStats
from models import SupportedLanguage
from ui.progress import ProgressState, create_progress, create_task, update_progress


class FileCategory(Enum):
    """
    Enumeration of file classification categories.

    Files are classified into one of these categories during the discovery phase
    to determine how they should be processed in subsequent pipeline stages.

    Attributes:
        LANGUAGE: Source code files matching the target language extensions.
        CONTEXT: High-value context files (docs, manifests, configs).
        IGNORE: Files that don't match any category and are excluded.
    """

    LANGUAGE = "lang"
    CONTEXT = "context"
    IGNORE = "ignore"


def get_focused_inventory(
    base_path: Path, language: SupportedLanguage
) -> Generator[Path, None, None]:
    """
    Scans the repository to identify potential module roots based on language-specific heuristics.

    This generator consumes the raw Git file stream and applies a "Language Sieve."
    It looks for specific manifest files (e.g., `package.json` for TypeScript, `Cargo.toml`
    for Rust) defined in `LANGUAGES_HEURISTICS` to identify directories that represent
    distinct modules or sub-projects within the repository.

    Args:
        base_path (Path): The absolute root path of the repository.
        language (SupportedLanguages): The enum representing the selected programming language,
            used to determine which manifest files to look for.

    Yields:
        Path: The relative path to the parent directory of a found manifest file,
        effectively identifying a module root (e.g., "src/backend" or ".").
    """

    git_client = GitClient(base_path)
    raw_stream = git_client.stream_file_paths()

    manifests = LANGUAGES_HEURISTICS[language]["manifests"]

    for file_path in raw_stream:
        rel_path = file_path.parent

        if file_path.name.lower() in manifests:
            yield rel_path


def get_final_inventory_file(
    base_path: Path, scopes: list[str], language: SupportedLanguage
) -> InventoryResult:
    """
    Filters the repository files into two distinct categories: Language files and Context files.

    This function runs a filtered `git ls-files` command scoped to the user-selected directories.
    It iterates through the file stream and assigns files to temporary inventory lists based on:
    1.  **Language Files:** Files matching the selected language's extensions (e.g., `.ts`, `.py`).
        These will later be processed by ctags.
    2.  **Context Files:** High-value text files (e.g., `README.md`, `package.json`) or universal
        configuration files defined in `UNIVERSAL_CONTEXT_FILES`. These will be read in full.

    Args:
        base_path (Path): The absolute root path of the repository.
        scopes (list[str]): A list of relative paths (modules) to restrict the git scan to.
        language (SupportedLanguages): The target language, used to determine valid code extensions.

    Returns:
        InventoryResult: An immutable result object containing:
            - source_inventory_path: Path to temporary file with language file paths
            - context_inventory_path: Path to temporary file with context file paths
            - stats: InventoryStats with counts of files in each category

    Note:
        The returned temporary files contain newline-separated relative file paths.
        The caller is responsible for cleaning up these temporary files after use.
    """

    pr("\n[bold magenta]🔍 Sifting through your codebase...")

    # Get the allowed extensions (e.g., {'.js', '.ts'})
    allowed_extensions = LANGUAGES_HEURISTICS[language]["extensions"]

    # Create the fast lookup set for the Reader (O(1) checks)
    tier_1_set: frozenset[str] = (
        frozenset(UNIVERSAL_CONTEXT_FILES) | LANGUAGES_HEURISTICS[language]["manifests"]
    )

    git_client = GitClient(base_path)
    total_files = git_client.count_files(scopes)
    file_stream = git_client.stream_file_paths(scopes)
    lang_file_count = 0
    ctx_file_count = 0

    with tempfile.NamedTemporaryFile(
        mode="w", delete=False, encoding="utf-8"
    ) as lang_file, tempfile.NamedTemporaryFile(
        mode="w", delete=False, encoding="utf-8"
    ) as context_file:
        with create_progress() as progress:
            task = create_task(
                progress,
                "Scanning files and applying language filter...",
                total=total_files,
            )

            for file_path in file_stream:
                # Advance the raw counter
                update_progress(progress, task, advance=1)

                # Check file category to know which file to write it to
                category = _classify_file(file_path, allowed_extensions, tier_1_set)
                if category == FileCategory.LANGUAGE:
                    lang_file_count += 1
                    lang_file.write(f"{file_path}\n")

                elif category == FileCategory.CONTEXT:
                    ctx_file_count += 1
                    context_file.write(f"{file_path}\n")

                update_progress(
                    progress,
                    task,
                    ProgressState.IN_PROGRESS,
                    description=f"Kept {lang_file_count + ctx_file_count} {language} files...",
                )

            # Final update
            update_progress(
                progress,
                task,
                ProgressState.COMPLETE,
                description=f"✅ Found {lang_file_count + ctx_file_count} valid files",
                completed=total_files,
            )

        return InventoryResult(
            Path(lang_file.name),
            Path(context_file.name),
            InventoryStats(
                lang_file_count,
                ctx_file_count,
            ),
        )


def _classify_file(
    path: Path, allowed_extensions: frozenset[str], tier_1_context: frozenset[str]
) -> FileCategory:
    """
    Classify a file into one of the FileCategory enum values.

    This pure function implements the classification logic used during file discovery.
    It checks file extensions and names against the provided sets to determine
    whether a file is source code, context, or should be ignored.

    Args:
        path: The Path object representing the file to classify.
        allowed_extensions: Set of file extensions (with dots, e.g., ".py", ".ts")
            that identify source code files for the target language.
        tier_1_context: Set of filenames (lowercase) that are considered high-priority
            context files, including universal context files and language-specific manifests.

    Returns:
        FileCategory: The classification result:
            - LANGUAGE if the file extension matches allowed_extensions
            - CONTEXT if the filename is in tier_1_context, starts with "readme", or has .md extension
            - IGNORE otherwise
    """
    file_name = path.name.lower()
    suffix = path.suffix.lower()

    # Check Language
    if suffix in allowed_extensions:
        return FileCategory.LANGUAGE

    # Check Context
    if file_name in tier_1_context or file_name.startswith("readme") or suffix == ".md":
        return FileCategory.CONTEXT

    return FileCategory.IGNORE
