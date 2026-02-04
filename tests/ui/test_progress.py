"""
Comprehensive tests for the progress module using pytest.

Tests cover:
- ProgressState: enum values and string representation
- create_progress: Rich Progress instance creation with correct columns
- create_task: task creation with description and total
- update_progress: progress updates with various parameters and error cases
"""

from unittest.mock import MagicMock, patch

import pytest

from ui.progress import (
    ProgressState,
    create_progress,
    create_task,
    update_progress,
)


# ============================================================================
# Tests for ProgressState
# ============================================================================


@pytest.mark.unit
def test_progress_state_values():
    """ProgressState should have correct enum values."""
    assert ProgressState.IN_PROGRESS == "magenta"
    assert ProgressState.COMPLETE == "green"
    assert ProgressState.WARNING == "yellow"
    assert ProgressState.ERROR == "red"


@pytest.mark.unit
def test_progress_state_string_representation():
    """ProgressState should be a StrEnum with string values."""
    assert str(ProgressState.IN_PROGRESS) == "magenta"
    assert str(ProgressState.COMPLETE) == "green"
    assert str(ProgressState.WARNING) == "yellow"
    assert str(ProgressState.ERROR) == "red"


@pytest.mark.unit
def test_progress_state_all_values():
    """ProgressState should have all expected states."""
    expected_states = {"IN_PROGRESS", "COMPLETE", "WARNING", "ERROR"}
    actual_states = {state.name for state in ProgressState}
    assert actual_states == expected_states


# ============================================================================
# Tests for create_progress
# ============================================================================


@pytest.mark.unit
def test_create_progress_returns_progress_instance():
    """create_progress should return a Rich Progress instance."""
    progress = create_progress()
    
    from rich.progress import Progress
    assert isinstance(progress, Progress)


@pytest.mark.unit
def test_create_progress_has_correct_columns():
    """create_progress should create Progress with correct column types."""
    from rich.progress import (
        BarColumn,
        SpinnerColumn,
        TaskProgressColumn,
        TextColumn,
    )
    
    progress = create_progress()
    
    # Check that progress has the expected columns
    # Rich Progress stores columns in _columns attribute
    columns = progress.columns
    assert len(columns) == 4
    
    # Verify column types (order matters)
    assert isinstance(columns[0], SpinnerColumn)
    assert isinstance(columns[1], TextColumn)
    assert isinstance(columns[2], BarColumn)
    assert isinstance(columns[3], TaskProgressColumn)


# ============================================================================
# Tests for create_task
# ============================================================================


@pytest.mark.unit
def test_create_task_with_total():
    """create_task should create a task with description and total."""
    progress = create_progress()
    
    task_id = create_task(progress, "Processing files", total=100)
    
    assert task_id is not None
    # Verify task exists in progress
    task = progress.tasks[task_id]
    assert task.description == f"[{ProgressState.IN_PROGRESS}]Processing files"
    assert task.total == 100


@pytest.mark.unit
def test_create_task_without_total():
    """create_task should create indeterminate task when total is None."""
    progress = create_progress()
    
    task_id = create_task(progress, "Processing files", total=None)
    
    assert task_id is not None
    task = progress.tasks[task_id]
    assert task.description == f"[{ProgressState.IN_PROGRESS}]Processing files"
    assert task.total is None  # Indeterminate


@pytest.mark.unit
def test_create_task_uses_in_progress_state():
    """create_task should use IN_PROGRESS state in description."""
    progress = create_progress()
    
    task_id = create_task(progress, "Test task", total=50)
    
    task = progress.tasks[task_id]
    assert ProgressState.IN_PROGRESS in task.description
    assert task.description.startswith(f"[{ProgressState.IN_PROGRESS}]")


@pytest.mark.unit
def test_create_task_multiple_tasks():
    """create_task should allow creating multiple tasks."""
    progress = create_progress()
    
    task1 = create_task(progress, "Task 1", total=10)
    task2 = create_task(progress, "Task 2", total=20)
    
    assert task1 != task2
    assert len(progress.tasks) == 2


# ============================================================================
# Tests for update_progress
# ============================================================================


@pytest.mark.unit
def test_update_progress_with_advance_only():
    """update_progress should advance progress without changing description."""
    progress = create_progress()
    task_id = create_task(progress, "Test task", total=100)
    
    # Update with just advance
    update_progress(progress, task_id, advance=10)
    
    task = progress.tasks[task_id]
    assert task.completed == 10


@pytest.mark.unit
def test_update_progress_with_completed():
    """update_progress should set absolute completed count."""
    progress = create_progress()
    task_id = create_task(progress, "Test task", total=100)
    
    update_progress(progress, task_id, completed=25)
    
    task = progress.tasks[task_id]
    assert task.completed == 25


@pytest.mark.unit
def test_update_progress_with_description_and_state():
    """update_progress should update description when state is provided."""
    progress = create_progress()
    task_id = create_task(progress, "Initial", total=100)
    
    update_progress(
        progress,
        task_id,
        progress_state=ProgressState.COMPLETE,
        description="Updated",
    )
    
    task = progress.tasks[task_id]
    assert task.description == f"[{ProgressState.COMPLETE}]Updated"


@pytest.mark.unit
def test_update_progress_with_state_and_advance():
    """update_progress should update both state/description and advance."""
    progress = create_progress()
    task_id = create_task(progress, "Initial", total=100)
    
    update_progress(
        progress,
        task_id,
        progress_state=ProgressState.IN_PROGRESS,
        description="Processing",
        advance=5,
    )
    
    task = progress.tasks[task_id]
    assert task.description == f"[{ProgressState.IN_PROGRESS}]Processing"
    assert task.completed == 5


@pytest.mark.unit
def test_update_progress_with_total():
    """update_progress should update total count."""
    progress = create_progress()
    task_id = create_task(progress, "Test task", total=100)
    
    update_progress(progress, task_id, total=200)
    
    task = progress.tasks[task_id]
    assert task.total == 200


@pytest.mark.unit
def test_update_progress_all_states():
    """update_progress should work with all ProgressState values."""
    progress = create_progress()
    task_id = create_task(progress, "Test", total=100)
    
    for state in ProgressState:
        update_progress(
            progress,
            task_id,
            progress_state=state,
            description=f"State {state.name}",
        )
        task = progress.tasks[task_id]
        assert task.description == f"[{state}]State {state.name}"


@pytest.mark.unit
def test_update_progress_state_without_description_raises_error():
    """update_progress should raise ValueError if state provided without description."""
    progress = create_progress()
    task_id = create_task(progress, "Test task", total=100)
    
    with pytest.raises(ValueError, match="progress_state and description must be provided together"):
        update_progress(progress, task_id, progress_state=ProgressState.COMPLETE)


@pytest.mark.unit
def test_update_progress_description_without_state_raises_error():
    """update_progress should raise ValueError if description provided without state."""
    progress = create_progress()
    task_id = create_task(progress, "Test task", total=100)
    
    with pytest.raises(ValueError, match="progress_state and description must be provided together"):
        update_progress(progress, task_id, description="New description")


@pytest.mark.unit
def test_update_progress_multiple_updates():
    """update_progress should handle multiple sequential updates."""
    progress = create_progress()
    task_id = create_task(progress, "Test task", total=100)
    
    # First update: advance by 10
    update_progress(progress, task_id, advance=10)
    assert progress.tasks[task_id].completed == 10
    
    # Second update: advance by 5 more
    update_progress(progress, task_id, advance=5)
    assert progress.tasks[task_id].completed == 15
    
    # Third update: set absolute value
    update_progress(progress, task_id, completed=50)
    assert progress.tasks[task_id].completed == 50


@pytest.mark.unit
def test_update_progress_with_none_description_preserves_existing():
    """update_progress should preserve existing description when description is None."""
    progress = create_progress()
    task_id = create_task(progress, "Initial description", total=100)
    original_description = progress.tasks[task_id].description
    
    # Update without description
    update_progress(progress, task_id, advance=10)
    
    # Description should be unchanged
    assert progress.tasks[task_id].description == original_description
