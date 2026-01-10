"""
Progress reporting callback protocol for decoupling UI from business logic.

This module defines a protocol that allows progress reporting to be abstracted
away from the core processing logic, making it easier to test and swap
implementations (e.g., Rich UI, logging, metrics).
"""

from types import TracebackType
from typing import Optional, Protocol

from rich.progress import Progress, TaskID
from ui.progress import (
    ProgressState,
    create_progress,
    create_task,
    update_progress,
)


class ProgressCallback(Protocol):
    """
    Protocol for progress reporting callbacks.

    This protocol defines the interface for reporting progress during long-running
    operations. Implementations can provide UI updates (Rich), logging, metrics,
    or no-op behavior for testing.

    The lifecycle is:
    1. Context manager entry (__enter__)
    2. on_start() - Called once at the beginning
    3. on_update() - Called multiple times during processing
    4. on_complete() - Called once at the end
    5. Context manager exit (__exit__)
    """

    def __enter__(self) -> "ProgressCallback":
        """Enter the progress callback context."""

    def __exit__(
        self,
        exc_type: Optional[type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        """Exit the progress callback context."""

    def on_start(self, description: str, total: int) -> None:
        """
        Initialize progress reporting for a new task.

        Args:
            total: Total number of items to process.
            description: Initial description text to display.
        """

    def on_update(
        self, *, advance: Optional[int] = None, description: Optional[str] = None
    ) -> None:
        """
        Update progress by advancing the counter, updating description, or both.

        Args:
            advance: Optional number of items processed since last update.
                If None, progress counter is not advanced.
            description: Optional description text to update. If None, keeps existing description.

        Note:
            At least one of `advance` or `description` must be provided.
            You can call:
            - `on_update(advance=5)` - just advance
            - `on_update(description="...")` - just update description
            - `on_update(advance=5, description="...")` - both
        """

    def on_complete(self, description: str, completed: int) -> None:
        """
        Mark the task as complete.

        Args:
            description: Final description text to display.
        """


class RichProgressCallback:
    """
    Rich UI implementation of ProgressCallback.

    This class wraps the existing Rich progress bar functionality, allowing
    the core processing logic to report progress without directly depending
    on Rich UI components.
    """

    def __init__(self) -> None:
        """Initialize the callback. Progress instance is created lazily."""
        self._progress: Optional[Progress] = None
        self._task: Optional[TaskID] = None

    def __enter__(self) -> "RichProgressCallback":
        """
        Enter the progress context (creates the Rich Progress instance).

        This allows RichProgressCallback to be used as a context manager,
        matching the pattern: `with RichProgressCallback() as callback:`
        """
        self._progress = create_progress()
        self._progress.__enter__()
        return self

    def __exit__(
        self,
        exc_type: Optional[type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        """Exit the progress context (cleans up Rich Progress)."""
        if self._progress:
            self._progress.__exit__(exc_type, exc_val, exc_tb)

    def on_start(self, description: str, total: Optional[int]) -> None:
        """
        Initialize progress reporting for a new task.

        Creates a new task in the Rich progress bar.
        """
        if not self._progress:
            raise RuntimeError(
                "RichProgressCallback must be used as a context manager. "
                "Use: with RichProgressCallback() as callback:"
            )
        self._task = create_task(self._progress, description, total=total)

    def on_update(
        self, *, advance: Optional[int] = None, description: Optional[str] = None
    ) -> None:
        """
        Update progress by advancing the counter, updating description, or both.

        If description is provided, also updates the description with IN_PROGRESS state.
        """
        if not self._progress:
            raise RuntimeError(
                "RichProgressCallback must be used as a context manager. "
                "Use: with RichProgressCallback() as callback:"
            )
        if self._task is None:
            raise RuntimeError("on_start() must be called before on_update()")

        # Validate that at least one parameter is provided
        if not (advance or description):
            raise ValueError(
                "At least one of 'advance' or 'description' must be provided to on_update()"
            )

        if description:
            # Update with description (and optionally advance)
            # When description is provided, we use IN_PROGRESS state
            update_progress(
                self._progress,
                self._task,
                ProgressState.IN_PROGRESS,
                advance=advance,
                description=description,
            )
        elif advance:
            # Update with just advance (keeps existing description)
            update_progress(
                self._progress,
                self._task,
                advance=advance,
            )

    def on_complete(
        self, description: str, completed: int, total: Optional[int] = None
    ) -> None:
        """
        Mark the task as complete.

        Updates the progress bar to show completion state.
        """
        if not self._progress:
            raise RuntimeError(
                "RichProgressCallback must be used as a context manager. "
                "Use: with RichProgressCallback() as callback:"
            )
        if self._task is None:
            raise RuntimeError("on_start() must be called before on_complete()")

        update_progress(
            self._progress,
            self._task,
            ProgressState.COMPLETE,
            completed=completed,
            total=total,
            description=description,
        )


class NoOpProgressCallback:
    """
    No-op implementation of ProgressCallback for testing.

    This implementation does nothing, allowing tests to run without
    Rich UI dependencies or actual progress bars.
    """

    def __enter__(self) -> "NoOpProgressCallback":
        """Enter the progress callback context (no-op)."""
        return self

    def __exit__(self, *args) -> None:
        """Exit the progress callback context (no-op)."""

    def on_start(self, description: str, total: int) -> None:
        """No-op: does nothing."""

    def on_update(
        self, *, advance: Optional[int] = None, description: Optional[str] = None
    ) -> None:
        """No-op: does nothing."""

    def on_complete(self, description: str, completed: int) -> None:
        """No-op: does nothing."""
