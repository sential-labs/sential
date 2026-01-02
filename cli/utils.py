"""
General utility functions for the CLI application.
"""

from pathlib import Path
from rich.console import Console

console: Console = Console()


def debug(
    *values: object,
    sep: str = " ",
    end: str = "\n",
) -> None:
    """
    Print debug message with orange bold formatting.

    This utility function formats and prints debug messages to the console using
    Rich's styling capabilities. It's designed for development and debugging purposes.

    Args:
        *values: Variable number of objects to print. All values are converted to strings.
        sep: Separator string between values. Defaults to a single space.
        end: String appended after the last value. Defaults to newline.

    Returns:
        None: This function only prints to console and returns nothing.
    """
    if not values:
        print(end=end)
        return

    # Convert all values to strings
    str_values = [str(v) for v in values]

    # Join with separator
    message = sep.join(str_values)

    # Print with formatting
    console.print(f"DEBUG: {message}", end=end, style="orange1")


def is_binary_file(file_path: Path) -> bool:
    """
    Determine if a file is binary by checking for null bytes and UTF-8 decodability.

    This function performs a fast heuristic check by reading the first 1024 bytes
    of the file and looking for null bytes (which are common in binary formats).
    It also attempts to decode the chunk as UTF-8 to catch encoding errors.

    Args:
        file_path: The path to the file to check.

    Returns:
        bool: True if the file appears to be binary, False if it's likely text.
            Also returns True if the file cannot be read or decoded.
    """
    try:
        with open(file_path, "rb") as f:
            chunk = f.read(1024)
            if b"\0" in chunk:
                return True
            chunk.decode("utf-8")
            return False
    except UnicodeDecodeError:
        return True
    except OSError:
        return True


def read_file_content(file_path: Path, is_tier_1: bool = False) -> str:
    """
    Reads the text content of a file with safety checks and intelligent truncation.

    Binary files are automatically detected and skipped. Text files are read up to a specific
    character limit based on their importance "Tier".
    - **Tier 1 (True):** Critical context files (Manifests, Docs). Limit: 100k chars.
    - **Tier 2 (False):** Standard files. Limit: 50k chars.

    Args:
        file_path (Path): The absolute path to the file to read.
        is_tier_1 (bool): If True, applies a higher character limit (100k). If False,
            applies the standard limit (50k). Defaults to False.

    Returns:
        str: The content of the file. If the file is binary, non-existent, or an error occurs,
        returns an empty string. If the content exceeds the limit, it is truncated with a notice.
    """

    limit = 100_000 if is_tier_1 else 50_000

    if not file_path.is_file():
        return ""

    # We skip binary files
    if is_binary_file(file_path):
        return ""

    try:
        with file_path.open("r", encoding="utf-8", errors="ignore") as f:
            # We read limit + 1 so we KNOW if there was more left behind
            content = f.read(limit + 1)

            if len(content) > limit:
                return (
                    content[:limit]
                    + f"\n\n... [TRUNCATED BY SENTIAL: File exceeded {limit} chars] ..."
                )

            return content
    except OSError:
        return ""
