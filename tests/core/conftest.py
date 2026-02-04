"""
Shared fixtures for core module tests.

This module provides reusable pytest fixtures for testing core functionality,
including mock factories, test data builders, and common test objects.
"""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from core.models import (
    FileCategory,
    FileMetadata,
    ProcessedFile,
    CategoryProcessedFiles,
)
from core.tokens import MockTokenBudget, NoOpTokenCounter
from ui.progress_display import NoOpProgressDisplay


@pytest.fixture
def project_root(tmp_path):
    """Create a temporary project root for testing."""
    return tmp_path / "project"


@pytest.fixture
def sample_file_metadata():
    """Sample FileMetadata for testing."""
    return FileMetadata(Path("file.py"), FileCategory.SOURCE)


@pytest.fixture
def mock_popen_factory():
    """Factory for creating mock Popen instances."""

    def _factory(stdout_lines):
        def mock_popen(*_args, **_kwargs):
            mock_process = MagicMock()
            mock_process.stdout = iter(stdout_lines)
            mock_process.__enter__ = MagicMock(return_value=mock_process)
            mock_process.__exit__ = MagicMock(return_value=None)
            return mock_process

        return mock_popen

    return _factory


@pytest.fixture
def token_counter():
    """Token counter for testing."""
    return NoOpTokenCounter(return_value=100)


@pytest.fixture
def token_budget():
    """Token budget for testing."""
    return MockTokenBudget(can_afford_return=True)


@pytest.fixture
def category_status():
    """CategoryProcessedFiles status for testing."""
    return CategoryProcessedFiles(FileCategory.SOURCE)


@pytest.fixture
def progress_display():
    """Progress display for testing."""
    return NoOpProgressDisplay()


@pytest.fixture
def tracking_progress_display():
    """Progress display that tracks calls for testing."""
    mock = MagicMock()
    mock.calls = []

    # Track calls in format: (method_name, *args) matching existing test expectations
    def make_tracker(method_name):
        def tracker(*args, **kwargs):
            # For on_update, kwargs are used (advance, description)
            if method_name == "update":
                mock.calls.append(
                    (method_name, kwargs.get("advance"), kwargs.get("description"))
                )
            else:
                # For on_start and on_complete, use positional args
                mock.calls.append((method_name, *args))

        return tracker

    mock.on_start = make_tracker("start")
    mock.on_update = make_tracker("update")
    mock.on_complete = make_tracker("complete")
    mock.__enter__ = MagicMock(return_value=mock)
    mock.__exit__ = MagicMock(return_value=None)

    return mock


@pytest.fixture
def processed_file_factory():
    """Factory for creating ProcessedFile instances."""

    def _factory(path="file.py", content="function foo"):
        return ProcessedFile(path, FileCategory.SOURCE.value, content)

    return _factory


@pytest.fixture
def mock_path_exists_factory():
    def _factory(import_path: str):
        def dynamic_exists(self):
            return "nonexistent" not in self.name

        return patch(
            f"{import_path}.Path.exists", autospec=True, side_effect=dynamic_exists
        )

    return _factory


@pytest.fixture
def mock_file_reader_factory():
    """Factory for creating MockFileReader instances with file content mappings."""

    def _factory(file_contents: dict[str, str]):
        """
        Create a MockFileReader configured with file content mappings.

        Args:
            file_contents: Dictionary mapping file names to their content.
                Keys are file names (e.g., "file1.md"), values are file content strings.

        Returns:
            MockFileReader instance configured to return content based on file name.
        """
        from core.file_io import MockFileReader

        def read_file_side_effect(path: Path) -> str:
            return file_contents.get(path.name, "")

        return MockFileReader(read_file_fn=read_file_side_effect)

    return _factory
