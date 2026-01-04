"""
Core data models for the discovery and inventory pipeline.

This module defines the data structures used to represent the results of
file discovery and classification operations within the Sential CLI.
"""

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path


@dataclass(frozen=True)
class InventoryStats:
    """
    Statistics regarding a file inventory scan operation.

    This immutable dataclass stores counts of files that were classified
    during the discovery phase. It provides a computed total property for convenience.

    Attributes:
        language_files: The number of source code files found (e.g., .py, .ts files).
        context_files: The number of context files found (e.g., README.md, package.json).

    Note:
        This is a frozen dataclass, so instances are immutable after creation.
    """

    language_files: int
    context_files: int

    @property
    def total(self) -> int:
        """
        Calculate the total number of valid files found.

        Returns:
            int: The sum of language_files and context_files.
        """
        return self.language_files + self.context_files


@dataclass(frozen=True)
class InventoryResult:
    """
    The result of the file discovery and classification operation.

    This immutable dataclass encapsulates the output of `get_final_inventory_file`,
    containing paths to temporary files that list discovered files and statistics
    about the scan operation. The temporary files contain newline-separated relative
    file paths that can be used for subsequent processing (e.g., ctags extraction).

    Attributes:
        source_inventory_path: Path to a temporary file containing relative paths
            of all source code files (language files) that match the target language.
        context_inventory_path: Path to a temporary file containing relative paths
            of all context files (documentation, manifests, configs) that were discovered.
        stats: An InventoryStats instance containing counts of files in each category.

    Note:
        This is a frozen dataclass, so instances are immutable after creation.
        The temporary files referenced by the paths should be cleaned up by the caller.
    """

    source_inventory_path: Path
    context_inventory_path: Path
    stats: InventoryStats


@dataclass(frozen=True)
class Ctag:
    path: str
    kind: str
    name: str


class RecordType(StrEnum):
    """Descriptive names for JSONL record types"""

    CONTEXT_FILE = "context_file"
