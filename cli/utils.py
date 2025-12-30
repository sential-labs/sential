"""
General utility functions for the CLI application.
"""

from rich.console import Console

console = Console()


def debug(
    *values: object,
    sep: str = " ",
    end: str = "\n",
) -> None:
    """Print debug message with orange bold formatting."""
    if not values:
        print(end=end)
        return

    # Convert all values to strings
    str_values = [str(v) for v in values]

    # Join with separator
    message = sep.join(str_values)

    # Print with formatting
    console.print(f"DEBUG: {message}", end=end, style="orange1")
