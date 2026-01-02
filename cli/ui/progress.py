"""
Creation and configuration for rich progress bars
"""

from enum import StrEnum
from typing import Optional

from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TaskID,
    TaskProgressColumn,
    TextColumn,
)


class ProgressState(StrEnum):
    IN_PROGRESS = "magenta"
    COMPLETE = "green"
    WARNING = "yellow"
    ERROR = "red"


def create_progress() -> Progress:
    """Factory function: Configures the 'look and feel' of our progress bars."""
    return Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
    )


def create_task(progress: Progress, description: str, total: float) -> TaskID:
    """Helper: Adds a specific task to an existing progress instance."""
    return progress.add_task(f"[{ProgressState.IN_PROGRESS}]{description}", total=total)


def update_progress(
    progress: Progress,
    task: TaskID,
    progress_state: Optional[ProgressState] = None,
    total: Optional[float] = None,
    completed: Optional[float] = None,
    advance: Optional[float] = None,
    description: Optional[str] = None,
) -> None:

    # Ensure they are in the same state (both truthy or both falsy)
    if bool(progress_state) != bool(description):
        raise ValueError("progress_state and description must be provided together.")

    if description:
        description = f"[{progress_state}]{description}"

    progress.update(
        task, total=total, completed=completed, advance=advance, description=description
    )
