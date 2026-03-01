"""
Core data models for the discovery and inventory pipeline.

This module defines the data structures used to represent the results of
file discovery and classification operations within the Sential CLI.
"""

from dataclasses import dataclass
from enum import Enum
from pathlib import Path


@dataclass(frozen=True)
class ProcessedFile:
    path: str
    type: str
    content: str


class FileCategory(Enum):
    CONTEXT = "context_file"
    MANIFEST = "manifest_file"
    SIGNAL = "signal_file"
    SOURCE = "source_file"
    CHAPTER_FILE = "chapter_file"
    UNKNOWN = "generic_file"


@dataclass
class FileMetadata:
    """
    Metadata container for file significance scoring and classification.

    This dataclass stores information about a file's path, computed significance score,
    and various classification flags that indicate the file's role in the codebase.
    It also computes derived attributes (normalized names, depth, parent directories)
    that are used during significance calculation.

    Attributes:
        file_path: The path to the file (absolute or relative).
        score: The computed significance score for this file. Higher scores indicate
            more important files. Defaults to 0.
        is_context: True if this is a universal context file (e.g., README.md, .cursorrules).
        is_manifest: True if this file matches a language-specific manifest pattern
            (e.g., package.json, requirements.txt, .csproj).
        is_signal: True if this file matches a signal pattern (e.g., main.py, index.ts).
            Signal files are entry points or key architectural files.
        is_source: True if this file has a source code extension for the target language.

    Computed Attributes (set in __post_init__):
        name_lower: Lowercase filename including extension (e.g., "readme.md").
        suffix_lower: Lowercase file extension (e.g., ".py", ".ts").
        stem_lower: Lowercase filename without extension (e.g., "main" from "main.py").
            Note: For multi-extension files like "file.tar.gz", stem is "file.tar".
        depth: Number of path components (directory levels). Root-level files have depth=1.
        file_parents: Set of lowercase parent directory names for matching against
            ignore patterns (e.g., {"src", "utils"} for "src/utils/file.py").
    """

    file_path: Path
    category: FileCategory = FileCategory.UNKNOWN
    score: int = 0

    def __post_init__(self):
        """Compute derived attributes from the file path."""
        self.name_lower = self.file_path.name.lower()  # includes extension
        self.suffix_lower = self.file_path.suffix.lower()
        self.depth = len(self.file_path.parts)
        self.file_parents = {str(p).lower() for p in self.file_path.parent.parts}
        # Removes extension
        # Note: if the file is file.tar.gz -> stem is file.tar
        self.stem_lower = self.file_path.stem.lower()


class CategoryProcessedFiles:
    def __init__(self, category: FileCategory) -> None:
        self.category: FileCategory = category
        self.files: list[ProcessedFile] = []

    def append(self, file: ProcessedFile) -> None:
        self.files.append(file)


@dataclass(frozen=True)
class Ctag:
    """
    Represents a code symbol (tag) extracted by Universal Ctags.

    This immutable dataclass stores information about a single code symbol found
    in a source file. It contains the file path where the symbol was found, the
    type/kind of symbol (e.g., "function", "class", "variable"), and the symbol's name.

    Attributes:
        path: The relative file path where this symbol was found.
        kind: The type of symbol (e.g., "function", "class", "variable", "method").
        name: The name of the symbol (e.g., function name, class name).
    """

    path: str
    kind: str
    name: str
