import contextlib
from dataclasses import asdict, dataclass, field
from enum import Enum
from itertools import islice
from pathlib import Path
import tempfile
from typing import Generator, Optional
import json
import subprocess
import tiktoken

from adapters.ctags import get_ctags_path
from constants import CTAGS_KINDS, LANGUAGES_HEURISTICS, UNIVERSAL_CONTEXT_FILES
from core.models import Ctag
from models import SupportedLanguage
from utils import read_file


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
    UNKNOWN = "generic_file"


class CategoryProcessedFilesStatus:
    def __init__(self, category: FileCategory, all_category_files_len: int) -> None:
        self.category: FileCategory = category
        self.all_category_files_len: int = all_category_files_len
        self.files: list[ProcessedFile] = []
        self.current_index: int = 0
        self.is_completed: bool = False

    def append(self, file: ProcessedFile) -> None:
        if self.current_index < self.all_category_files_len:
            self.files.append(file)
            self.current_index += 1
        else:
            self.is_completed = True


class TokenCounter:
    def __init__(self, model_name: str = "gpt-4o"):
        try:
            self.encoder = tiktoken.encoding_for_model(model_name)
        except KeyError:
            self.encoder = tiktoken.get_encoding("cl100k_base")

    def count(self, text: Optional[str]) -> int:
        if not text:
            return 0
        return len(self.encoder.encode(text))


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


@dataclass(frozen=True)
class TokenLimits:
    """Immutable policy defining the maximum allowed tokens per category."""

    max_total: int = 200_000
    ratios: dict[FileCategory, float] = field(
        default_factory=lambda: {
            FileCategory.CONTEXT: 0.1,
            FileCategory.MANIFEST: 0.05,
            FileCategory.SIGNAL: 0.05,
            FileCategory.SOURCE: 0.4,
        }
    )


class TokenBudget:
    """Mutable state tracker for a single extraction job."""

    def __init__(self, limits: TokenLimits):
        self.limits = limits
        # Derived budgets
        self.remaining: dict[FileCategory, int] = {
            cat: int(self.limits.max_total * ratio)
            for cat, ratio in limits.ratios.items()
        }

    def can_afford(self, category: FileCategory, count: int) -> bool:
        return self.remaining.get(category, 0) >= count

    def spend(self, category: FileCategory, count: int) -> None:
        if category in self.remaining:
            self.remaining[category] -= count


def categorize_files(
    raw_stream: Generator[Path, None, None], language: SupportedLanguage
) -> dict[FileCategory, list[FileMetadata]]:
    files_by_category: dict[FileCategory, list[FileMetadata]] = {
        category: [] for category in FileCategory
    }

    for file_path in raw_stream:
        print(file_path.resolve())
        file_metadata = calculate_significance(file_path, language)
        files_by_category[file_metadata.category].append(file_metadata)

    return files_by_category


def process_files(
    root: Path,
    files_by_category: dict[FileCategory, list[FileMetadata]],
) -> dict[FileCategory, CategoryProcessedFilesStatus]:

    counter = TokenCounter("gpt-4o")
    token_budget = TokenBudget(TokenLimits())

    processing_order = [
        FileCategory.CONTEXT,
        FileCategory.MANIFEST,
        FileCategory.SIGNAL,
        FileCategory.SOURCE,
    ]

    status_results: dict[FileCategory, CategoryProcessedFilesStatus] = {}

    for category in processing_order:
        files_in_category = files_by_category[category]
        if not files_in_category:
            continue

        files_in_category.sort(
            key=lambda file_meta: (file_meta.score, -file_meta.depth), reverse=True
        )

        status = CategoryProcessedFilesStatus(category, len(files_in_category))

        if category == FileCategory.SOURCE:
            extract_ctags_for_source_files(
                root,
                files_in_category,
                counter,
                token_budget,
                status,
            )
        else:
            process_files_for_category(
                root,
                files_in_category,
                counter,
                token_budget,
                status,
            )

        status_results[category] = status

    return status_results


def write_processed_files(
    results: dict[FileCategory, CategoryProcessedFilesStatus],
) -> Path:
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
    output_path = Path(tempfile.gettempdir()) / "sential_payload.jsonl"
    with open(output_path, "w", encoding="utf-8") as out_f:
        for _, status in results.items():
            for processed_file in status.files:
                out_f.write(json.dumps(asdict(processed_file)) + "\n")

    return output_path


def process_files_for_category(
    root: Path,
    files: list[FileMetadata],
    counter: TokenCounter,
    token_budget: TokenBudget,
    status: CategoryProcessedFilesStatus,
) -> None:

    category = status.category

    for file_meta in islice(files, status.current_index, None):
        full_path = root / file_meta.file_path
        if not full_path.exists():
            continue

        content = read_file(full_path)

        token_usage = counter.count(content)
        if token_budget.can_afford(category, token_usage):
            token_budget.spend(category, token_usage)
            status.append(
                ProcessedFile(str(file_meta.file_path), category.value, content)
            )
        else:
            status.is_completed = True
            break


def calculate_significance(
    file_path: Path, language: SupportedLanguage
) -> FileMetadata:
    """
    Calculate a significance score for a file based on language-specific heuristics.

    This function assigns a numerical score to files based on their importance for
    context generation. Higher scores indicate files that are more valuable for
    understanding the codebase structure and intent.

    Scoring Rules (in priority order):
        1. Universal Context Files (score: 1000 - (depth * 5))
           - Files in UNIVERSAL_CONTEXT_FILES (e.g., README.md, .cursorrules)
           - Any file starting with "readme" (case-insensitive)
           - Any file with .md extension
           - These files get a base score of 1000, but still have depth penalty applied
           - Example: Root-level README.md (depth=1) scores 995, nested docs/README.md (depth=2) scores 990

        2. Manifest Files (score: +80)
           - Exact filename matches (e.g., "package.json", "requirements.txt")
           - Extension matches for manifests starting with "." (e.g., ".csproj", ".sln")
           - This handles both filename-based manifests (Python, JS, Java, Go) and
             extension-based manifests (C# .csproj files)

        3. Signal Files (score: +60)
           - Files where the stem (filename without extension) matches a signal name
             AND the extension matches a language extension
           - Examples: "main.py" (stem="main", extension=".py"), "index.ts" (stem="index", extension=".ts")

        4. Source Files (score: +50)
           - Files with extensions matching the language's source extensions
           - Only applies if the file is not a manifest or signal file
           - Examples: "utils.py" (extension=".py"), "helper.ts" (extension=".ts")

        5. Path Depth Penalty (score: -5 per directory level)
           - Applied to all files (including universal context files)
           - Shallow files (near root) are considered more architectural
           - Example: "src/main.py" (depth=2) scores better than "src/utils/helpers/main.py" (depth=4)

        6. Ignored Directory Penalty (score: -100)
           - Files in ignored directories (e.g., "tests", "mocks", "examples")
           - Applied if any parent directory matches an ignore pattern

    Args:
        file_path: The path to the file being scored. Can be absolute or relative.
        language: The target programming language for context extraction.

    Returns:
        A FileMetadata object with the file's significance score and metadata flags.
        The score is stored in the `score` attribute. Higher scores indicate more
        important files. Universal context files get a base score of 1000 minus depth penalty.
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

    # 3. Path Depth Penalty (shallow is usually more architectural)
    meta.score = scores[meta.category]
    meta.score -= meta.depth * 5

    # 4. Check if any of the file's parents is in ignore_dirs
    if any(ignore_dir in meta.file_parents for ignore_dir in ignore_dirs):
        meta.score -= 100

    return meta


def extract_ctags_for_source_files(
    root: Path,
    files: list[FileMetadata],
    counter: TokenCounter,
    token_budget: TokenBudget,
    status: CategoryProcessedFilesStatus,
) -> None:
    """
    Extracts code symbols from source files using Universal Ctags and processes them.

    This function runs ctags on multiple source files, parses the JSON output, and formats
    all valid symbols into strings. The output is used for token counting and budget management.

    Args:
        files: List of FileMetadata objects for source files to process.
        counter: TokenCounter instance for counting tokens.
        token_budget: TokenBudget instance for managing token limits.
        status: CategoryProcessedFilesStatus to track processing state.
    """

    with contextlib.closing(_stream_ctags_output(root, files, status)) as tag_stream:
        for file_path, skeleton_content in tag_stream:
            token_usage = counter.count(skeleton_content)

            if token_budget.can_afford(status.category, token_usage):
                token_budget.spend(status.category, token_usage)
                status.append(
                    ProcessedFile(file_path, status.category.value, skeleton_content)
                )
            else:
                status.is_completed = True
                break


def _stream_ctags_output(
    root: Path, files: list[FileMetadata], status: CategoryProcessedFilesStatus
) -> Generator[tuple[str, str], None, None]:
    ctags_path = get_ctags_path()
    terminator = "###END_FILE###"

    # Flags:
    # --output-format=json: easier parsing
    # --fields=+n: give us line numbers
    # --filter: run in "interactive" mode (keep process alive)
    cmd = [
        str(ctags_path),
        "--output-format=json",
        "--sort=no",
        "--fields=+n",
        "--filter",
        f"--filter-terminator={terminator}",
    ]

    try:
        with subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            # If we don't pass this and 5000 files emit warnings
            # The OS pipe buffer will fill up, and since we're not
            # reading them except when we crash, ctags will wait
            # for the buffer to clear, the script waits for ctags
            # to finish the current file -> Deadlock
            stderr=subprocess.DEVNULL,
            text=True,
            encoding="utf-8",
            errors="replace",  # CRITICAL: Don't crash if Ctags outputs weird chars
            bufsize=1,
        ) as process:

            if not (process.stdin and process.stdout):
                return

            for file_meta in islice(files, status.current_index, None):
                full_path = root / file_meta.file_path
                if not full_path.exists():
                    continue

                # Send input
                try:
                    process.stdin.write(str(full_path) + "\n")
                    # Even though we use line buffer (bufsize=1) and we append "\n"
                    # it's still better to flush explicitly to be safe
                    process.stdin.flush()
                except (BrokenPipeError, OSError):
                    # Ctags crashed or was closed
                    return

                current_file_tags: list[str] = []
                while True:
                    raw_line = process.stdout.readline()
                    # Empty string from readline() means EOF (stream closed) - exit loop
                    if raw_line == "":
                        return

                    raw_line = raw_line.strip()
                    # Empty string after strip means blank/whitespace-only line - skip it
                    if not raw_line:
                        continue

                    if raw_line == terminator:
                        break

                    ctag = _parse_tag_line(raw_line)
                    print(full_path, ctag)
                    if ctag:
                        current_file_tags.append(format_tag(ctag.kind, ctag.name))
                yield str(file_meta.file_path), "\n".join(current_file_tags)
    except (OSError, subprocess.SubprocessError):
        return


def _parse_tag_line(line: str) -> Optional[Ctag]:
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
