"""
Comprehensive tests for the processing module using pytest.

Tests cover:
- process_files: processing files by category with token budget management
- process_readable_files_for_category: reading and processing readable files for CONTEXT, MANIFEST, SIGNAL categories
"""

from pathlib import Path
import pytest

from core.processing import process_files, process_readable_files_for_category
from core.models import (
    FileCategory,
    FileMetadata,
    CategoryProcessedFiles,
)
from core.file_io import MockFileReader
from core.exceptions import FileReadError
from core.tokens import MockTokenBudget


# ============================================================================
# Tests for process_files
# ============================================================================


@pytest.mark.unit
@pytest.mark.mock
def test_process_files_all_categories(
    project_root,
    token_counter,
    token_budget,
    mocker,
):
    """Should process files for all categories in correct order."""
    files_by_category = {
        FileCategory.CONTEXT: [
            FileMetadata(Path("README.md"), FileCategory.CONTEXT, score=1000)
        ],
        FileCategory.MANIFEST: [
            FileMetadata(Path("package.json"), FileCategory.MANIFEST, score=900)
        ],
        FileCategory.SIGNAL: [
            FileMetadata(Path("main.py"), FileCategory.SIGNAL, score=800)
        ],
        FileCategory.SOURCE: [
            FileMetadata(Path("file.py"), FileCategory.SOURCE, score=700)
        ],
    }

    mock_extract_ctags = mocker.patch("core.processing.extract_ctags_for_source_files")
    mock_process_readable = mocker.patch(
        "core.processing.process_readable_files_for_category"
    )

    result = process_files(
        root=project_root,
        files_by_category=files_by_category,
        counter=token_counter,
        token_budget=token_budget,
    )

    # Verify all categories are in results
    assert FileCategory.CONTEXT in result
    assert FileCategory.MANIFEST in result
    assert FileCategory.SIGNAL in result
    assert FileCategory.SOURCE in result

    # Verify SOURCE category called extract_ctags
    mock_extract_ctags.assert_called_once()
    call_args = mock_extract_ctags.call_args
    assert call_args[0][0] == project_root
    assert len(call_args[0][1]) == 1
    assert call_args[0][1][0].file_path == Path("file.py")

    # Verify other categories called process_readable_files_for_category
    assert mock_process_readable.call_count == 3


@pytest.mark.unit
@pytest.mark.mock
def test_process_files_empty_categories_skipped(
    project_root,
    token_counter,
    token_budget,
    mocker,
):
    """Should skip empty categories and not add them to results."""
    files_by_category = {
        FileCategory.CONTEXT: [],
        FileCategory.MANIFEST: [
            FileMetadata(Path("package.json"), FileCategory.MANIFEST, score=900)
        ],
        FileCategory.SIGNAL: [],
        FileCategory.SOURCE: [],
    }

    mock_extract_ctags = mocker.patch("core.processing.extract_ctags_for_source_files")
    mock_process_readable = mocker.patch(
        "core.processing.process_readable_files_for_category"
    )

    result = process_files(
        root=project_root,
        files_by_category=files_by_category,
        counter=token_counter,
        token_budget=token_budget,
    )

    # Empty categories should NOT be in results (they are skipped)
    assert FileCategory.CONTEXT not in result
    assert FileCategory.MANIFEST in result
    assert FileCategory.SIGNAL not in result
    assert FileCategory.SOURCE not in result

    # Only MANIFEST should have been processed
    mock_process_readable.assert_called_once()
    mock_extract_ctags.assert_not_called()


@pytest.mark.unit
@pytest.mark.mock
def test_process_files_sorts_by_score_and_depth(
    project_root,
    token_counter,
    token_budget,
    mocker,
):
    """Should sort files by score (descending) and depth (ascending)."""
    files_by_category = {
        FileCategory.CONTEXT: [
            FileMetadata(Path("low_score.md"), FileCategory.CONTEXT, score=100),
            FileMetadata(Path("high_score.md"), FileCategory.CONTEXT, score=1000),
            FileMetadata(Path("medium_score.md"), FileCategory.CONTEXT, score=500),
        ],
        FileCategory.MANIFEST: [],
        FileCategory.SIGNAL: [],
        FileCategory.SOURCE: [],
    }

    mock_process_readable = mocker.patch(
        "core.processing.process_readable_files_for_category"
    )

    process_files(
        root=project_root,
        files_by_category=files_by_category,
        counter=token_counter,
        token_budget=token_budget,
    )

    # Verify files were sorted correctly
    call_args = mock_process_readable.call_args
    sorted_files = call_args[0][1]
    assert sorted_files[0].file_path == Path("high_score.md")
    assert sorted_files[0].score == 1000
    assert sorted_files[1].file_path == Path("medium_score.md")
    assert sorted_files[1].score == 500
    assert sorted_files[2].file_path == Path("low_score.md")
    assert sorted_files[2].score == 100


@pytest.mark.unit
@pytest.mark.mock
def test_process_files_sorts_by_depth_when_scores_equal(
    project_root,
    token_counter,
    token_budget,
    mocker,
):
    """Should sort by depth (ascending) when scores are equal."""
    files_by_category = {
        FileCategory.CONTEXT: [
            FileMetadata(Path("deep/nested/file.md"), FileCategory.CONTEXT, score=100),
            FileMetadata(Path("file.md"), FileCategory.CONTEXT, score=100),
            FileMetadata(Path("nested/file.md"), FileCategory.CONTEXT, score=100),
        ],
        FileCategory.MANIFEST: [],
        FileCategory.SIGNAL: [],
        FileCategory.SOURCE: [],
    }

    mock_process_readable = mocker.patch(
        "core.processing.process_readable_files_for_category"
    )

    process_files(
        root=project_root,
        files_by_category=files_by_category,
        counter=token_counter,
        token_budget=token_budget,
    )

    # Verify files were sorted by depth (ascending) when scores are equal
    call_args = mock_process_readable.call_args
    sorted_files = call_args[0][1]
    assert sorted_files[0].file_path == Path("file.md")
    assert sorted_files[0].depth == 1
    assert sorted_files[1].file_path == Path("nested/file.md")
    assert sorted_files[1].depth == 2
    assert sorted_files[2].file_path == Path("deep/nested/file.md")
    assert sorted_files[2].depth == 3


@pytest.mark.unit
@pytest.mark.mock
def test_process_files_creates_default_counter_and_budget(
    project_root,
    mocker,
):
    """Should create default TiktokenCounter and PooledTokenBudget when None."""
    files_by_category = {
        FileCategory.CONTEXT: [
            FileMetadata(Path("README.md"), FileCategory.CONTEXT, score=1000)
        ],
        FileCategory.MANIFEST: [],
        FileCategory.SIGNAL: [],
        FileCategory.SOURCE: [],
    }

    mock_tiktoken = mocker.patch("core.processing.TiktokenCounter")
    mock_pooled = mocker.patch("core.processing.PooledTokenBudget")
    mocker.patch("core.processing.process_readable_files_for_category")

    process_files(
        root=project_root,
        files_by_category=files_by_category,
        counter=None,
        token_budget=None,
    )

    # Verify defaults were created
    mock_tiktoken.assert_called_once_with("gpt-4o")
    mock_pooled.assert_called_once()


@pytest.mark.unit
@pytest.mark.mock
def test_process_files_uses_injected_counter_and_budget(
    project_root,
    token_counter,
    token_budget,
    mocker,
):
    """Should use injected counter and token_budget when provided."""
    files_by_category = {
        FileCategory.CONTEXT: [
            FileMetadata(Path("README.md"), FileCategory.CONTEXT, score=1000)
        ],
        FileCategory.MANIFEST: [],
        FileCategory.SIGNAL: [],
        FileCategory.SOURCE: [],
    }

    mock_tiktoken = mocker.patch("core.processing.TiktokenCounter")
    mock_pooled = mocker.patch("core.processing.PooledTokenBudget")
    mock_process_readable = mocker.patch(
        "core.processing.process_readable_files_for_category"
    )

    process_files(
        root=project_root,
        files_by_category=files_by_category,
        counter=token_counter,
        token_budget=token_budget,
    )

    # Verify defaults were NOT created
    mock_tiktoken.assert_not_called()
    mock_pooled.assert_not_called()

    # Verify injected dependencies were used
    call_args = mock_process_readable.call_args
    assert call_args[0][2] == token_counter
    assert call_args[0][3] == token_budget


# ============================================================================
# Tests for process_readable_files_for_category
# ============================================================================


@pytest.mark.unit
@pytest.mark.mock
def test_process_readable_files_context_category(
    project_root,
    token_counter,
    token_budget,
    progress_display,
    mock_path_exists_factory,
):
    """Should process CONTEXT category files successfully."""
    files = [FileMetadata(Path("README.md"), FileCategory.CONTEXT, score=1000)]
    status = CategoryProcessedFiles(FileCategory.CONTEXT)

    # Mock file existence and reading
    mock_reader = MockFileReader(return_value="Project documentation")

    patcher = mock_path_exists_factory("core.processing")
    with patcher:
        process_readable_files_for_category(
            root=project_root,
            files=files,
            counter=token_counter,
            token_budget=token_budget,
            status=status,
            progress_display=progress_display,
            file_reader=mock_reader,
        )

    # Verify file was processed
    assert len(status.files) == 1
    assert status.files[0].path == "README.md"
    assert status.files[0].content == "Project documentation"
    assert status.files[0].type == FileCategory.CONTEXT.value

    # Verify token budget was called
    assert len(token_budget.start_category_calls) == 1
    assert token_budget.start_category_calls[0] == FileCategory.CONTEXT


@pytest.mark.unit
@pytest.mark.mock
def test_process_readable_files_manifest_category(
    project_root,
    token_counter,
    token_budget,
    progress_display,
    mock_path_exists_factory,
):
    """Should process MANIFEST category files successfully."""
    files = [FileMetadata(Path("package.json"), FileCategory.MANIFEST, score=900)]
    status = CategoryProcessedFiles(FileCategory.MANIFEST)

    # Mock file existence and reading
    mock_reader = MockFileReader(return_value='{"name": "test"}')

    patcher = mock_path_exists_factory("core.processing")
    with patcher:
        process_readable_files_for_category(
            root=project_root,
            files=files,
            counter=token_counter,
            token_budget=token_budget,
            status=status,
            progress_display=progress_display,
            file_reader=mock_reader,
        )

    # Verify file was processed
    assert len(status.files) == 1
    assert status.files[0].path == "package.json"
    assert status.files[0].type == FileCategory.MANIFEST.value

    # Verify token budget was called
    assert len(token_budget.start_category_calls) == 1
    assert token_budget.start_category_calls[0] == FileCategory.MANIFEST


@pytest.mark.unit
@pytest.mark.mock
def test_process_readable_files_signal_category(
    project_root,
    token_counter,
    token_budget,
    progress_display,
    mock_path_exists_factory,
):
    """Should process SIGNAL category files successfully."""
    files = [FileMetadata(Path("main.py"), FileCategory.SIGNAL, score=800)]
    status = CategoryProcessedFiles(FileCategory.SIGNAL)

    # Mock file existence and reading
    mock_reader = MockFileReader(return_value="def main(): pass")

    patcher = mock_path_exists_factory("core.processing")
    with patcher:
        process_readable_files_for_category(
            root=project_root,
            files=files,
            counter=token_counter,
            token_budget=token_budget,
            status=status,
            progress_display=progress_display,
            file_reader=mock_reader,
        )

    # Verify file was processed
    assert len(status.files) == 1
    assert status.files[0].path == "main.py"
    assert status.files[0].type == FileCategory.SIGNAL.value

    # Verify token budget was called
    assert len(token_budget.start_category_calls) == 1
    assert token_budget.start_category_calls[0] == FileCategory.SIGNAL


@pytest.mark.unit
@pytest.mark.mock
def test_process_readable_files_multiple_files(
    project_root,
    token_counter,
    token_budget,
    progress_display,
    mock_path_exists_factory,
    mock_file_reader_factory,
):
    """Should process multiple files in order."""
    files = [
        FileMetadata(Path("file1.md"), FileCategory.CONTEXT, score=1000),
        FileMetadata(Path("file2.md"), FileCategory.CONTEXT, score=900),
        FileMetadata(Path("file3.md"), FileCategory.CONTEXT, score=800),
    ]
    status = CategoryProcessedFiles(FileCategory.CONTEXT)

    # Mock file existence and reading
    mock_reader = mock_file_reader_factory(
        {
            "file1.md": "Content 1",
            "file2.md": "Content 2",
            "file3.md": "Content 3",
        }
    )

    patcher = mock_path_exists_factory("core.processing")
    with patcher:
        process_readable_files_for_category(
            root=project_root,
            files=files,
            counter=token_counter,
            token_budget=token_budget,
            status=status,
            progress_display=progress_display,
            file_reader=mock_reader,
        )

    # Verify all files were processed
    assert len(status.files) == 3
    assert status.files[0].path == "file1.md"
    assert status.files[1].path == "file2.md"
    assert status.files[2].path == "file3.md"


@pytest.mark.unit
@pytest.mark.mock
def test_process_readable_files_skips_nonexistent_files(
    project_root,
    token_counter,
    token_budget,
    progress_display,
    mock_path_exists_factory,
    mock_file_reader_factory,
):
    """Should skip files that don't exist."""
    files = [
        FileMetadata(Path("exists.md"), FileCategory.CONTEXT, score=1000),
        FileMetadata(Path("nonexistent.md"), FileCategory.CONTEXT, score=900),
        FileMetadata(Path("also_exists.md"), FileCategory.CONTEXT, score=800),
    ]
    status = CategoryProcessedFiles(FileCategory.CONTEXT)

    # Mock file existence and reading
    mock_reader = mock_file_reader_factory(
        {
            "exists.md": "Content 1",
            "also_exists.md": "Content 3",
        }
    )
    patcher = mock_path_exists_factory("core.processing")
    with patcher:
        process_readable_files_for_category(
            root=project_root,
            files=files,
            counter=token_counter,
            token_budget=token_budget,
            status=status,
            progress_display=progress_display,
            file_reader=mock_reader,
        )

    # Verify only existing files were processed
    assert len(status.files) == 2
    assert status.files[0].path == "exists.md"
    assert status.files[1].path == "also_exists.md"


@pytest.mark.unit
@pytest.mark.mock
def test_process_readable_files_handles_file_read_error(
    project_root,
    token_counter,
    token_budget,
    progress_display,
    mock_path_exists_factory,
):
    """Should handle FileReadError gracefully and continue processing."""
    files = [
        FileMetadata(Path("file1.md"), FileCategory.CONTEXT, score=1000),
        FileMetadata(Path("file2.md"), FileCategory.CONTEXT, score=900),
    ]
    status = CategoryProcessedFiles(FileCategory.CONTEXT)

    # Mock file existence

    # Create mock file reader that raises error for second file
    def read_file_side_effect(path: Path) -> str:
        if path.name == "file2.md":
            raise FileReadError(
                "Permission denied", str(path), original_exception=OSError()
            )
        return "Content"

    mock_reader = MockFileReader(read_file_fn=read_file_side_effect)

    patcher = mock_path_exists_factory("core.processing")
    with patcher:
        process_readable_files_for_category(
            root=project_root,
            files=files,
            counter=token_counter,
            token_budget=token_budget,
            status=status,
            progress_display=progress_display,
            file_reader=mock_reader,
        )

    # Verify first file was processed, second was skipped
    assert len(status.files) == 1
    assert status.files[0].path == "file1.md"


@pytest.mark.unit
@pytest.mark.mock
def test_process_readable_files_respects_token_budget(
    project_root,
    token_counter,
    progress_display,
    mock_path_exists_factory,
    mock_file_reader_factory,
):
    """Should stop processing when token budget is exhausted."""
    files = [
        FileMetadata(Path("file1.md"), FileCategory.CONTEXT, score=1000),
        FileMetadata(Path("file2.md"), FileCategory.CONTEXT, score=900),
        FileMetadata(Path("file3.md"), FileCategory.CONTEXT, score=800),
    ]
    status = CategoryProcessedFiles(FileCategory.CONTEXT)

    # Create budget that can only afford first file
    call_count = [0]

    def can_afford_side_effect(_count: int) -> bool:
        call_count[0] += 1
        # Can afford first file, but not second
        return call_count[0] == 1

    budget = MockTokenBudget(can_afford_fn=can_afford_side_effect)

    # Mock file existence and reading
    mock_reader = mock_file_reader_factory(
        {
            "file1.md": "Content 1",
            "file2.md": "Content 2",
            "file3.md": "Content 3",
        }
    )

    patcher = mock_path_exists_factory("core.processing")
    with patcher:
        process_readable_files_for_category(
            root=project_root,
            files=files,
            counter=token_counter,
            token_budget=budget,
            status=status,
            progress_display=progress_display,
            file_reader=mock_reader,
        )

    # Verify only first file was processed
    assert len(status.files) == 1
    assert status.files[0].path == "file1.md"


@pytest.mark.unit
@pytest.mark.mock
def test_process_readable_files_uses_injected_file_reader(
    project_root,
    token_counter,
    token_budget,
    progress_display,
    mock_path_exists_factory,
):
    """Should use injected file_reader instead of default."""
    files = [FileMetadata(Path("file.md"), FileCategory.CONTEXT, score=1000)]
    status = CategoryProcessedFiles(FileCategory.CONTEXT)

    # Create mock file reader
    mock_reader = MockFileReader(return_value="Mock content")

    patcher = mock_path_exists_factory("core.processing")
    with patcher:
        process_readable_files_for_category(
            root=project_root,
            files=files,
            counter=token_counter,
            token_budget=token_budget,
            status=status,
            progress_display=progress_display,
            file_reader=mock_reader,
        )

    # Verify mock reader was called
    assert len(mock_reader.read_file_calls) == 1
    assert status.files[0].content == "Mock content"


@pytest.mark.unit
@pytest.mark.mock
def test_process_readable_files_uses_injected_progress_display(
    project_root,
    token_counter,
    token_budget,
    tracking_progress_display,
    mock_path_exists_factory,
):
    """Should use injected progress_display instead of default."""
    files = [FileMetadata(Path("file.md"), FileCategory.CONTEXT, score=1000)]
    status = CategoryProcessedFiles(FileCategory.CONTEXT)

    # Mock file existence and reading
    mock_reader = MockFileReader(return_value="Content")

    patcher = mock_path_exists_factory("core.processing")
    with patcher:
        process_readable_files_for_category(
            root=project_root,
            files=files,
            counter=token_counter,
            token_budget=token_budget,
            status=status,
            progress_display=tracking_progress_display,
            file_reader=mock_reader,
        )

    # Verify progress display was called
    assert len(tracking_progress_display.calls) >= 2
    assert any(call[0] == "start" for call in tracking_progress_display.calls)
    assert any(call[0] == "complete" for call in tracking_progress_display.calls)


@pytest.mark.unit
@pytest.mark.mock
def test_process_readable_files_calls_token_budget_methods(
    project_root,
    token_counter,
    token_budget,
    progress_display,
    mock_path_exists_factory,
    mock_file_reader_factory,
):
    """Should call token_budget.start_category, can_afford, and spend correctly."""
    files = [
        FileMetadata(Path("file1.md"), FileCategory.CONTEXT, score=1000),
        FileMetadata(Path("file2.md"), FileCategory.CONTEXT, score=900),
    ]
    status = CategoryProcessedFiles(FileCategory.CONTEXT)

    # Mock file existence and reading
    mock_reader = mock_file_reader_factory(
        {
            "file1.md": "Content 1",
            "file2.md": "Content 2",
        }
    )

    patcher = mock_path_exists_factory("core.processing")
    with patcher:
        process_readable_files_for_category(
            root=project_root,
            files=files,
            counter=token_counter,
            token_budget=token_budget,
            status=status,
            progress_display=progress_display,
            file_reader=mock_reader,
        )

    # Verify token budget methods were called
    assert len(token_budget.start_category_calls) == 1
    assert token_budget.start_category_calls[0] == FileCategory.CONTEXT
    assert len(token_budget.can_afford_calls) == 2  # One per file
    assert len(token_budget.spend_calls) == 2  # One per file


@pytest.mark.unit
@pytest.mark.mock
def test_process_readable_files_empty_file_list(
    project_root,
    token_counter,
    token_budget,
    progress_display,
):
    """Should handle empty file list gracefully."""
    files = []
    status = CategoryProcessedFiles(FileCategory.CONTEXT)

    process_readable_files_for_category(
        root=project_root,
        files=files,
        counter=token_counter,
        token_budget=token_budget,
        status=status,
        progress_display=progress_display,
    )

    # Verify no files were processed
    assert len(status.files) == 0
    # But token budget should still be called
    assert len(token_budget.start_category_calls) == 1


@pytest.mark.unit
@pytest.mark.mock
def test_process_readable_files_all_nonexistent(
    project_root,
    token_counter,
    token_budget,
    progress_display,
):
    """Should handle case where all files don't exist."""
    files = [
        FileMetadata(Path("nonexistent1.md"), FileCategory.CONTEXT, score=1000),
        FileMetadata(Path("nonexistent2.md"), FileCategory.CONTEXT, score=900),
    ]
    status = CategoryProcessedFiles(FileCategory.CONTEXT)

    process_readable_files_for_category(
        root=project_root,
        files=files,
        counter=token_counter,
        token_budget=token_budget,
        status=status,
        progress_display=progress_display,
    )

    # Verify no files were processed
    assert len(status.files) == 0
    # Token budget should still be called
    assert len(token_budget.start_category_calls) == 1
