"""
Progress bar creation and management module using Rich.

This module provides utilities for creating and managing progress bars throughout
the Sential CLI. It uses the Rich library to display styled progress indicators
with spinners, bars, and task descriptions. The module supports different progress
states (in progress, complete, warning, error) with color coding.
"""

from enum import StrEnum

from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TaskID,
    TaskProgressColumn,
    TextColumn,
)


class ProgressState(StrEnum):
    """
    Enumeration of progress bar states with associated color codes.

    Each state represents a different phase or outcome of a task, and the color
    is used to visually distinguish the state in the progress bar display.

    Attributes:
        IN_PROGRESS: Magenta color for tasks currently being processed.
        COMPLETE: Green color for successfully completed tasks.
        WARNING: Yellow color for tasks with warnings or non-critical issues.
        ERROR: Red color for tasks that have encountered errors.
    """

    IN_PROGRESS = "magenta"
    COMPLETE = "green"
    WARNING = "yellow"
    ERROR = "red"


def create_progress() -> Progress:
    """
    Creates and configures a Rich Progress instance with standard styling.

    Factory function that sets up a progress bar with a spinner, description text,
    progress bar, and task progress column. This provides a consistent look and
    feel across all progress indicators in the application.

    Returns:
        A configured Rich Progress instance ready for task management.
    """
    return Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
    )


def create_task(progress: Progress, description: str, total: int | None) -> TaskID:
    """
    Creates a new task in a progress instance with initial state.

    Adds a task to the progress bar with the specified description and total
    count. The task is initialized with the IN_PROGRESS state (magenta color).

    Args:
        progress: The Rich Progress instance to add the task to.
        description: The description text to display for this task.
        total: The total number of items or steps for this task. If None,
            progress is indeterminate (no progress bar shown).

    Returns:
        TaskID: The unique identifier for the created task, used for updates.
    """
    return progress.add_task(f"[{ProgressState.IN_PROGRESS}]{description}", total=total)


def update_progress(
    progress: Progress,
    task: TaskID,
    progress_state: ProgressState | None = None,
    total: float | None = None,
    completed: float | None = None,
    advance: float | None = None,
    description: str | None = None,
) -> None:
    """
    Updates a progress task with new state, progress, or description.

    This function provides a unified interface for updating progress tasks. It
    supports updating the completion count, advancing by a delta, changing the
    total, updating the description, and changing the visual state (color).

    Note: If `progress_state` is provided, `description` must also be provided,
    and vice versa. This ensures the description is properly styled with the
    state color.

    Args:
        progress: The Rich Progress instance containing the task.
        task: The identifier of the task to update.
        progress_state: The new state to apply (affects color). Must be provided
            together with description.
        total: The new total count for the task. If None, the existing total
            is unchanged.
        completed: The absolute number of completed items. Mutually exclusive
            with `advance`.
        advance: The number of items to advance by (relative). Mutually
            exclusive with `completed`.
        description: The new description text. Must be provided together with
            progress_state.

    Raises:
        ValueError: If progress_state and description are not both provided
            or both omitted (they must be in sync).
    """
    # Ensure they are in the same state (both truthy or both falsy)
    if bool(progress_state) != bool(description):
        raise ValueError("progress_state and description must be provided together.")

    if description:
        description = f"[{progress_state}]{description}"

    # Only pass description if it's not None to preserve existing description
    # Rich's progress.update() treats None as "clear", so we omit it entirely
    if description is not None:
        progress.update(
            task,
            total=total,
            completed=completed,
            advance=advance,
            description=description,
        )
    else:
        progress.update(task, total=total, completed=completed, advance=advance)
