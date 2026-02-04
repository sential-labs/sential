"""
Comprehensive tests for the progress_display module using pytest.

Tests cover:
- RichProgressDisplay: context manager, on_start, on_update, on_complete, error cases
- NoOpProgressDisplay: basic functionality (no-op behavior)

Note: RichProgressDisplay tests use mocks to avoid creating actual Rich UI components.
"""

from unittest.mock import MagicMock, patch

import pytest

from ui.progress_display import NoOpProgressDisplay, RichProgressDisplay
from ui.progress import ProgressState


# ============================================================================
# Tests for RichProgressDisplay
# ============================================================================


@pytest.mark.unit
@pytest.mark.mock
def test_rich_progress_display_context_manager(mocker):
    """RichProgressDisplay should work as a context manager."""
    mocker.patch("ui.progress_display.create_progress")

    display = RichProgressDisplay()

    with display as rpd:
        assert rpd is display
        assert display._progress is not None


@pytest.mark.unit
@pytest.mark.mock
def test_rich_progress_display_enter_creates_progress(mocker):
    """__enter__ should create and enter the progress instance."""
    mock_progress = MagicMock()
    mock_create = mocker.patch("ui.progress_display.create_progress")
    mock_create.return_value = mock_progress

    display = RichProgressDisplay()
    result = display.__enter__()

    assert result is display
    assert display._progress is mock_progress
    mock_progress.__enter__.assert_called_once()


@pytest.mark.unit
@pytest.mark.mock
def test_rich_progress_display_exit_cleans_up(mocker):
    """__exit__ should clean up the progress instance."""
    mock_progress = MagicMock()
    mocker.patch("ui.progress_display.create_progress", return_value=mock_progress)

    display = RichProgressDisplay()
    display.__enter__()
    display.__exit__(None, None, None)

    mock_progress.__exit__.assert_called_once_with(None, None, None)


@pytest.mark.unit
@pytest.mark.mock
def test_rich_progress_display_exit_with_exception(mocker):
    """__exit__ should handle exceptions correctly."""
    mock_progress = MagicMock()
    mocker.patch("ui.progress_display.create_progress", return_value=mock_progress)

    display = RichProgressDisplay()
    display.__enter__()

    exc_type = ValueError
    exc_val = ValueError("Test error")
    exc_tb = None

    display.__exit__(exc_type, exc_val, exc_tb)

    mock_progress.__exit__.assert_called_once_with(exc_type, exc_val, exc_tb)


@pytest.mark.unit
@pytest.mark.mock
def test_rich_progress_display_exit_without_progress(mocker):
    """__exit__ should handle case when progress is None."""
    display = RichProgressDisplay()

    # Should not raise error even if progress is None
    display.__exit__(None, None, None)


@pytest.mark.unit
@pytest.mark.mock
def test_rich_progress_display_on_start_with_total(mocker):
    """on_start should create a task with description and total."""
    mock_progress = MagicMock()
    mock_task_id = MagicMock()
    mocker.patch("ui.progress_display.create_progress", return_value=mock_progress)
    mock_create_task = mocker.patch("ui.progress_display.create_task")
    mock_create_task.return_value = mock_task_id

    display = RichProgressDisplay()
    with display:
        display.on_start("Processing files", total=100)

    mock_create_task.assert_called_once_with(
        mock_progress, "Processing files", total=100
    )
    assert display._task is mock_task_id


@pytest.mark.unit
@pytest.mark.mock
def test_rich_progress_display_on_start_without_total(mocker):
    """on_start should create indeterminate task when total is None."""
    mock_progress = MagicMock()
    mock_task_id = MagicMock()
    mocker.patch("ui.progress_display.create_progress", return_value=mock_progress)
    mock_create_task = mocker.patch("ui.progress_display.create_task")
    mock_create_task.return_value = mock_task_id

    display = RichProgressDisplay()
    with display:
        display.on_start("Processing files", total=None)

    mock_create_task.assert_called_once_with(
        mock_progress, "Processing files", total=None
    )


@pytest.mark.unit
@pytest.mark.mock
def test_rich_progress_display_on_start_without_context_raises_error():
    """on_start should raise RuntimeError if not used as context manager."""
    display = RichProgressDisplay()

    with pytest.raises(RuntimeError, match="must be used as a context manager"):
        display.on_start("Test", total=100)


@pytest.mark.unit
@pytest.mark.mock
def test_rich_progress_display_on_update_with_advance_only(mocker):
    """on_update should update progress with advance only."""
    mock_progress = MagicMock()
    mock_task_id = MagicMock()
    mocker.patch("ui.progress_display.create_progress", return_value=mock_progress)
    mocker.patch("ui.progress_display.create_task", return_value=mock_task_id)
    mock_update = mocker.patch("ui.progress_display.update_progress")

    display = RichProgressDisplay()
    with display:
        display.on_start("Test", total=100)
        display.on_update(advance=5)

    mock_update.assert_called_with(
        mock_progress,
        mock_task_id,
        advance=5,
    )


@pytest.mark.unit
@pytest.mark.mock
def test_rich_progress_display_on_update_with_description_only(mocker):
    """on_update should update progress with description only."""
    mock_progress = MagicMock()
    mock_task_id = MagicMock()
    mocker.patch("ui.progress_display.create_progress", return_value=mock_progress)
    mocker.patch("ui.progress_display.create_task", return_value=mock_task_id)
    mock_update = mocker.patch("ui.progress_display.update_progress")

    display = RichProgressDisplay()
    with display:
        display.on_start("Test", total=100)
        display.on_update(description="New description")

    mock_update.assert_called_with(
        mock_progress,
        mock_task_id,
        ProgressState.IN_PROGRESS,
        advance=None,
        description="New description",
    )


@pytest.mark.unit
@pytest.mark.mock
def test_rich_progress_display_on_update_with_both(mocker):
    """on_update should update progress with both advance and description."""
    mock_progress = MagicMock()
    mock_task_id = MagicMock()
    mocker.patch("ui.progress_display.create_progress", return_value=mock_progress)
    mocker.patch("ui.progress_display.create_task", return_value=mock_task_id)
    mock_update = mocker.patch("ui.progress_display.update_progress")

    display = RichProgressDisplay()
    with display:
        display.on_start("Test", total=100)
        display.on_update(advance=10, description="Processing item")

    mock_update.assert_called_with(
        mock_progress,
        mock_task_id,
        ProgressState.IN_PROGRESS,
        advance=10,
        description="Processing item",
    )


@pytest.mark.unit
@pytest.mark.mock
def test_rich_progress_display_on_update_without_params_raises_error(mocker):
    """on_update should raise ValueError if neither advance nor description provided."""
    mock_progress = MagicMock()
    mock_task_id = MagicMock()
    mocker.patch("ui.progress_display.create_progress", return_value=mock_progress)
    mocker.patch("ui.progress_display.create_task", return_value=mock_task_id)

    display = RichProgressDisplay()
    with display:
        display.on_start("Test", total=100)

        with pytest.raises(
            ValueError,
            match="At least one of 'advance' or 'description' must be provided",
        ):
            display.on_update()


@pytest.mark.unit
@pytest.mark.mock
def test_rich_progress_display_on_update_without_context_raises_error():
    """on_update should raise RuntimeError if not used as context manager."""
    display = RichProgressDisplay()

    with pytest.raises(RuntimeError, match="must be used as a context manager"):
        display.on_update(advance=5)


@pytest.mark.unit
@pytest.mark.mock
def test_rich_progress_display_on_update_without_on_start_raises_error(mocker):
    """on_update should raise RuntimeError if on_start was not called first."""
    mock_progress = MagicMock()
    mocker.patch("ui.progress_display.create_progress", return_value=mock_progress)

    display = RichProgressDisplay()
    with display:
        with pytest.raises(
            RuntimeError, match="on_start\\(\\) must be called before on_update\\(\\)"
        ):
            display.on_update(advance=5)


@pytest.mark.unit
@pytest.mark.mock
def test_rich_progress_display_on_complete(mocker):
    """on_complete should update progress with COMPLETE state."""
    mock_progress = MagicMock()
    mock_task_id = MagicMock()
    mocker.patch("ui.progress_display.create_progress", return_value=mock_progress)
    mocker.patch("ui.progress_display.create_task", return_value=mock_task_id)
    mock_update = mocker.patch("ui.progress_display.update_progress")

    display = RichProgressDisplay()
    with display:
        display.on_start("Test", total=100)
        display.on_complete("Completed", completed=100, total=100)

    mock_update.assert_called_with(
        mock_progress,
        mock_task_id,
        ProgressState.COMPLETE,
        completed=100,
        total=100,
        description="Completed",
    )


@pytest.mark.unit
@pytest.mark.mock
def test_rich_progress_display_on_complete_without_total(mocker):
    """on_complete should work without total parameter."""
    mock_progress = MagicMock()
    mock_task_id = MagicMock()
    mocker.patch("ui.progress_display.create_progress", return_value=mock_progress)
    mocker.patch("ui.progress_display.create_task", return_value=mock_task_id)
    mock_update = mocker.patch("ui.progress_display.update_progress")

    display = RichProgressDisplay()
    with display:
        display.on_start("Test", total=100)
        display.on_complete("Completed", completed=100)

    mock_update.assert_called_with(
        mock_progress,
        mock_task_id,
        ProgressState.COMPLETE,
        completed=100,
        total=None,
        description="Completed",
    )


@pytest.mark.unit
@pytest.mark.mock
def test_rich_progress_display_on_complete_without_context_raises_error():
    """on_complete should raise RuntimeError if not used as context manager."""
    display = RichProgressDisplay()

    with pytest.raises(RuntimeError, match="must be used as a context manager"):
        display.on_complete("Completed", completed=100)


@pytest.mark.unit
@pytest.mark.mock
def test_rich_progress_display_on_complete_without_on_start_raises_error(mocker):
    """on_complete should raise RuntimeError if on_start was not called first."""
    mock_progress = MagicMock()
    mocker.patch("ui.progress_display.create_progress", return_value=mock_progress)

    display = RichProgressDisplay()
    with display:
        with pytest.raises(
            RuntimeError, match="on_start\\(\\) must be called before on_complete\\(\\)"
        ):
            display.on_complete("Completed", completed=100)


@pytest.mark.unit
@pytest.mark.mock
def test_rich_progress_display_full_lifecycle(mocker):
    """RichProgressDisplay should work through full lifecycle."""
    mock_progress = MagicMock()
    mock_task_id = MagicMock()
    mocker.patch("ui.progress_display.create_progress", return_value=mock_progress)
    mocker.patch("ui.progress_display.create_task", return_value=mock_task_id)
    mock_update = mocker.patch("ui.progress_display.update_progress")

    display = RichProgressDisplay()
    with display:
        display.on_start("Processing files", total=100)
        display.on_update(advance=10)
        display.on_update(advance=20, description="Processing batch")
        display.on_complete("Done", completed=100)

    # Verify calls
    assert mock_update.call_count == 3
    # First update: just advance
    assert mock_update.call_args_list[0][1]["advance"] == 10
    # Second update: advance and description
    assert mock_update.call_args_list[1][1]["advance"] == 20
    assert mock_update.call_args_list[1][1]["description"] == "Processing batch"
    # Complete: COMPLETE state (passed as positional argument, 3rd position)
    assert mock_update.call_args_list[2][0][2] == ProgressState.COMPLETE
    assert mock_update.call_args_list[2][1]["completed"] == 100


# ============================================================================
# Tests for NoOpProgressDisplay
# ============================================================================


@pytest.mark.unit
def test_noop_progress_display_context_manager():
    """NoOpProgressDisplay should work as a context manager."""
    display = NoOpProgressDisplay()

    with display as noop:
        assert noop is display


@pytest.mark.unit
def test_noop_progress_display_on_start():
    """NoOpProgressDisplay.on_start should do nothing."""
    display = NoOpProgressDisplay()

    # Should not raise any errors
    display.on_start("Test", total=100)
    display.on_start("Test 2", total=None)


@pytest.mark.unit
def test_noop_progress_display_on_update():
    """NoOpProgressDisplay.on_update should do nothing."""
    display = NoOpProgressDisplay()

    # Should not raise any errors
    display.on_update(advance=5)
    display.on_update(description="Test")
    display.on_update(advance=10, description="Test 2")
    display.on_update()  # Even with no params, should not raise


@pytest.mark.unit
def test_noop_progress_display_on_complete():
    """NoOpProgressDisplay.on_complete should do nothing."""
    display = NoOpProgressDisplay()

    # Should not raise any errors
    display.on_complete("Completed", completed=100)
    display.on_complete("Done", completed=50, total=100)


@pytest.mark.unit
def test_noop_progress_display_full_lifecycle():
    """NoOpProgressDisplay should work through full lifecycle without errors."""
    display = NoOpProgressDisplay()

    with display:
        display.on_start("Processing", total=100)
        display.on_update(advance=10)
        display.on_update(description="Processing item")
        display.on_complete("Done", completed=100)

    # Should complete without any errors
