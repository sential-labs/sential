"""
Context file reading and processing module.

This module handles the reading and prioritization of context files (e.g., README files,
manifest files, configuration files) that provide important project context. It processes
these files in a priority order, with universal context files and language-specific
manifests taking precedence over other files.
"""

import io
import json
from pathlib import Path

from constants import LANGUAGES_HEURISTICS, UNIVERSAL_CONTEXT_FILES
from core.models import RecordType
from models import SupportedLanguage
from ui.progress import ProgressState, create_progress, create_task, update_progress
from utils import read_file_content


def load_context_files(context_path: Path) -> set[Path]:
    """
    Loads context file paths from a text file into a set.

    Reads a file containing one file path per line, strips whitespace, and returns
    a set of Path objects for all non-empty lines.

    Args:
        context_path (Path): Path to the file containing context file paths,
            one per line.

    Returns:
        set[Path]: A set of Path objects representing the context files to process.
    """
    valid_context_path_objs: set[Path] = set()
    with open(context_path, "r", encoding="utf-8") as f:
        valid_context_path_objs = {
            Path(file_path.strip()) for file_path in f if file_path.strip()
        }
    return valid_context_path_objs


def build_priority_list(language: SupportedLanguage) -> list[str]:
    """
    Builds an ordered priority list of context file names.

    Creates a list where universal context files (e.g., README.md) have higher
    priority than language-specific manifests (e.g., package.json). The order
    is preserved, with duplicates removed while maintaining first occurrence.

    Args:
        language (SupportedLanguage): The target language, used to determine
            which language-specific manifests to include.

    Returns:
        list[str]: An ordered list of file names (not paths) in priority order.
    """
    return list(
        dict.fromkeys(
            UNIVERSAL_CONTEXT_FILES + tuple(LANGUAGES_HEURISTICS[language]["manifests"])
        )
    )


def find_matching_files(candidate: str, context_files: set[Path]) -> list[Path]:
    """
    Finds all context files that match a candidate file name.

    Performs case-insensitive matching on file names and returns matches sorted
    by depth (shallowest first), so root-level files are prioritized over nested ones.

    Args:
        candidate (str): The file name to match against (e.g., "package.json").
        context_files (set[Path]): A set of Path objects to search through.

    Returns:
        list[Path]: A list of matching Path objects, sorted by depth (shallowest first).
    """
    # Find matches for this candidate
    # We create a list of matches so we don't modify the set while iterating
    matches: list[Path] = []
    for context_file in context_files:

        if context_file.name.lower() == candidate.lower():
            matches.append(context_file)

    # Sort matches by depth (Root files first!)
    # "package.json" (depth 0) comes before "backend/package.json" (depth 1)
    matches.sort(key=lambda p: len(p.parents))
    return matches


def write_context_record(
    out_f: io.TextIOWrapper, relative_path: Path, content: str
) -> None:
    """
    Writes a context file record to the output file in JSONL format.

    Creates a JSON record containing the file path, record type, and full file content,
    then writes it as a single line to the output file.

    Args:
        out_f (io.TextIOWrapper): An open file handle (write mode) where the record
            will be written.
        relative_path (Path): The relative path of the context file.
        content (str): The full content of the context file.
    """
    ctx_record = {
        "path": str(relative_path),
        "type": RecordType.CONTEXT_FILE,
        "content": content,
    }
    out_f.write(json.dumps(ctx_record) + "\n")


def process_context_files(
    root_path: Path,
    context_path: Path,
    out_f: io.TextIOWrapper,
    language: SupportedLanguage,
    ctx_file_count: int,
) -> None:
    """
    Processes all context files and writes them to the output in priority order.

    This function performs a two-phase processing:
    1. Priority pass: Processes files matching the priority list (universal context
       files and language-specific manifests) in order, writing them first.
    2. Remaining files: Processes any remaining context files, sorted by depth.

    All files are read, validated, and written as context records to the output file.
    Progress is tracked and displayed throughout the process.

    Args:
        root_path (Path): The absolute root path of the repository.
        context_path (Path): Path to the temporary file listing context file paths.
        out_f (io.TextIOWrapper): An open file handle (write mode) where context
            records will be written in JSONL format.
        language (SupportedLanguage): The target language, used to determine
            priority order for manifests.
        ctx_file_count (int): The total number of context files to process,
            used for progress bar initialization.
    """
    # Create the Ordered List for the Writer (Preserve Priority)
    ordered_candidates = build_priority_list(language)
    # A. Load valid context files found by Git into a set
    context_files: set[Path] = load_context_files(context_path)

    with create_progress() as progress:
        task = create_task(
            progress,
            f"Reading from {ctx_file_count} context files...",
            total=ctx_file_count,
        )
        # B. The Priority Pass (Write the VIPs first)
        # We take each candidate in order, maintaining prio
        # candidates are names not relative paths
        for candidate in ordered_candidates:
            # Find matches for this candidate
            # We create a list of matches so we don't modify the set while iterating
            matches: list[Path] = find_matching_files(candidate, context_files)

            # Write them and remove from the pool
            if matches:
                for match in matches:
                    full_path = root_path / match
                    content = read_file_content(full_path, True)
                    if content:
                        write_context_record(out_f, match, content)
                        update_progress(
                            progress,
                            task,
                            ProgressState.IN_PROGRESS,
                            description=f"Included {match}...",
                            advance=1,
                        )

                    # Remove from the main set so it's not handled again
                    context_files.remove(match)

        # We handle whatever was left, anything that didn't match prev step
        leftovers = sorted(list(context_files), key=lambda p: len(p.parents))
        for leftover in leftovers:
            full_path = root_path / leftover
            content = read_file_content(full_path, True)

            if content:
                write_context_record(out_f, leftover, content)
                update_progress(
                    progress,
                    task,
                    ProgressState.IN_PROGRESS,
                    description=f"Included {leftover}...",
                    advance=1,
                )
        update_progress(
            progress,
            task,
            ProgressState.COMPLETE,
            description=f"✅ Processed {ctx_file_count} context files",
            completed=ctx_file_count,
        )
