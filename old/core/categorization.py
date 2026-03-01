"""File categorization and significance scoring module.

This module provides functionality to categorize files in a codebase based on their
role and importance. Files are classified into categories (Context, Manifest, Signal,
Source, or Unknown) and assigned significance scores that reflect their value for
understanding the codebase structure.

The categorization process uses language-specific heuristics to identify:
- Universal context files (README.md, .cursorrules, etc.)
- Project manifest files (package.json, requirements.txt, etc.)
- Entry point signal files (main.py, index.ts, etc.)
- Regular source code files

Significance scoring considers:
- File category (base score)
- Path depth (shallow files score higher)
- Ignored directories (tests/, mocks/, etc. receive penalties)

This module is used during codebase analysis to prioritize which files should be
included in context generation for better understanding of project structure.
"""

from pathlib import Path
from rich import print as pr
from constants import LANGUAGES_HEURISTICS, UNIVERSAL_CONTEXT_FILES
from core.models import FileCategory, FileMetadata
from models import SupportedLanguage
from ui.progress_display import ProgressDisplay, RichProgressDisplay


def categorize_files(
    file_paths: list[Path],
    total_files: int,
    language: SupportedLanguage,
    progress_display: ProgressDisplay | None = None,
) -> dict[FileCategory, list[FileMetadata]]:
    """
    Categorize files by their significance and role in the codebase.

    This function processes a list of file paths and categorizes each file based on
    language-specific heuristics. Files are assigned to categories (Context, Manifest,
    Signal, Source, or Unknown) and given significance scores that reflect their
    importance for understanding the codebase structure.

    The function uses `calculate_significance` to score each file, then groups them
    by category. Progress reporting is handled through the optional progress display
    parameter, allowing for UI updates during processing.

    Args:
        file_paths: List of file paths to categorize. Can be absolute or relative paths.
        total_files: Total number of files being processed. Used for progress reporting
            and should match the length of `file_paths` for accurate progress updates.
        language: The target programming language for context extraction. Determines
            which heuristics (manifests, signals, extensions, ignore patterns) are used.
        progress_display: Optional progress display implementation for reporting
            progress during categorization. If None, defaults to `RichProgressDisplay`.
            For testing, pass `NoOpProgressDisplay()` to avoid UI dependencies.

    Returns:
        A dictionary mapping each `FileCategory` to a list of `FileMetadata` objects
        for files in that category. The dictionary includes all categories, even if
        some are empty lists. Categories are:
        - `FileCategory.CONTEXT`: Universal context files (README.md, .cursorrules, etc.)
        - `FileCategory.MANIFEST`: Project manifest files (package.json, requirements.txt, etc.)
        - `FileCategory.SIGNAL`: Entry point files (main.py, index.ts, etc.)
        - `FileCategory.SOURCE`: Regular source code files
        - `FileCategory.UNKNOWN`: Files that don't match any category

    Example:
        >>> from pathlib import Path
        >>> from models import SupportedLanguage
        >>> from ui.progress_display import NoOpProgressDisplay
        >>>
        >>> files = [Path("main.py"), Path("README.md"), Path("utils.py")]
        >>> result = categorize_files(
        ...     files,
        ...     total_files=3,
        ...     language=SupportedLanguage.PY,
        ...     progress_display=NoOpProgressDisplay()
        ... )
        >>> # result[FileCategory.SIGNAL] contains main.py
        >>> # result[FileCategory.CONTEXT] contains README.md
        >>> # result[FileCategory.SOURCE] contains utils.py

    Note:
        Progress updates are sent in 10% increments (e.g., for 100 files, updates
        occur every 10 files processed). The final completion message includes
        the count of relevant files (excluding UNKNOWN category files).
    """

    files_by_category: dict[FileCategory, list[FileMetadata]] = {
        category: [] for category in FileCategory
    }

    pr("\n[bold magenta]🔍 Sifting through your codebase...")

    items_processed = 0
    # Increase progress by 10% increments, but at least 1 to avoid division by zero
    # If total_files is 0, advance will be 1 but we won't update (no files to process)
    advance = max(1, int(total_files * 0.1)) if total_files > 0 else 1

    rich_progress_display = (
        progress_display if progress_display is not None else RichProgressDisplay()
    )

    with rich_progress_display as rpd:
        rpd.on_start(
            f"Categorizing {total_files} files...",
            total=total_files,
        )
        for file_path in file_paths:
            file_metadata = calculate_significance(file_path, language)
            files_by_category[file_metadata.category].append(file_metadata)

            items_processed += 1
            if items_processed % advance == 0:
                rpd.on_update(advance=advance)

        kept_files_count = sum(
            len(f)
            for cat, f in files_by_category.items()
            if cat != FileCategory.UNKNOWN
        )
        rpd.on_complete(
            f"✅ Found {kept_files_count} relevant files.", completed=total_files
        )

    return files_by_category


def calculate_significance(
    file_path: Path, language: SupportedLanguage
) -> FileMetadata:
    """
    Calculate a significance score for a file based on language-specific heuristics.

    This function assigns a numerical score to files based on their importance for
    context generation. Higher scores indicate files that are more valuable for
    understanding the codebase structure and intent.

    Scoring Rules (applied in priority order):
        1. Category Assignment (determines base score):
           a. Universal Context Files (base: 1000)
              - Files in UNIVERSAL_CONTEXT_FILES (e.g., README.md, .cursorrules)
              - Any file starting with "readme" (case-insensitive)
              - Any file with .md extension
           b. Manifest Files (base: 80)
              - Exact filename matches (e.g., "package.json", "requirements.txt")
              - Extension matches for manifests starting with "." (e.g., ".csproj", ".sln")
              - Handles both filename-based (Python, JS, Java, Go) and extension-based (C#) manifests
           c. Signal Files (base: 60)
              - Files where stem matches a signal name AND extension matches language extensions
              - Examples: "main.py" (stem="main", ext=".py"), "index.ts" (stem="index", ext=".ts")
           d. Source Files (base: 50)
              - Files with extensions matching the language's source extensions
              - Only applies if not already categorized as manifest or signal
           e. Unknown Files (base: 0)
              - Files that don't match any category

        2. Path Depth Penalty (-5 per directory level beyond root)
           - Applied to all files after category assignment, but NOT to root-level files (depth=1)
           - Root-level files (depth=1) have no depth penalty
           - Files at depth=2 get -5 penalty, depth=3 get -10, etc.
           - Shallow files (near root) are considered more architectural
           - Example: "src/main.py" (depth=2) gets -5 penalty, "src/utils/main.py" (depth=3) gets -10

        3. Ignored Directory Penalty (-100)
           - Applied if any parent directory matches an ignore pattern
           - Examples: "tests/", "mocks/", "examples/"

    Final Score Formula:
        score = base_score - (max(0, (depth - 1)) * 5) - (100 if in ignored directory else 0)

    Examples:
        - Root-level README.md: 1000 (no depth penalty)
        - src/main.py (signal, depth=2): 60 - 5 = 55
        - tests/main.py (signal, depth=2, ignored dir): 60 - 5 - 100 = -45

    Args:
        file_path: The path to the file being scored. Can be absolute or relative.
        language: The target programming language for context extraction.

    Returns:
        A FileMetadata object with the file's category and significance score.
        The score is stored in the `score` attribute. Higher scores indicate more
        important files.
    """

    heuristics = LANGUAGES_HEURISTICS[language]
    manifests = heuristics["manifests"]
    signals = heuristics["signals"]
    extensions = heuristics["extensions"]
    ignore_dirs = heuristics["ignore_dirs"]

    meta = FileMetadata(file_path)

    # Universal Context (Highest Priority)
    if (
        meta.name_lower in UNIVERSAL_CONTEXT_FILES
        or meta.name_lower.startswith("readme")
        or meta.suffix_lower == ".md"
    ):
        meta.category = FileCategory.CONTEXT

    # Heuristics Match

    # Check for exact filename match (e.g., "global.json", "pom.xml")
    # or extension match for manifests that start with "." (e.g., ".csproj", ".sln")
    elif meta.name_lower in manifests or meta.suffix_lower in manifests:
        meta.category = FileCategory.MANIFEST

    # We look for all valid combinations of signal + extension
    elif meta.stem_lower in signals and meta.suffix_lower in extensions:
        meta.category = FileCategory.SIGNAL

    # Is it a source file
    elif meta.suffix_lower in extensions:
        meta.category = FileCategory.SOURCE

    # How much is each file category worth
    scores = {
        FileCategory.CONTEXT: 1000,
        FileCategory.MANIFEST: 80,
        FileCategory.SIGNAL: 60,
        FileCategory.SOURCE: 50,
        FileCategory.UNKNOWN: 0,
    }

    # 2. Path Depth Penalty (shallow is usually more architectural)
    # Root-level files (depth=1) have no penalty, only files deeper than root get penalized
    meta.score = scores[meta.category]
    if meta.depth > 1:
        meta.score -= (meta.depth - 1) * 5

    # 3. Check if any of the file's parents is in ignore_dirs
    if any(ignore_dir in meta.file_parents for ignore_dir in ignore_dirs):
        meta.score -= 100

    return meta
