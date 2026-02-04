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
