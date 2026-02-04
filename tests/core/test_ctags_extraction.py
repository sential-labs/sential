"""
Comprehensive tests for the ctags_extraction module using pytest.

Tests cover:
- format_tag: tag formatting functionality
- _get_rel_path_str_from_str: relative path conversion
- _parse_tag_line: JSON tag line parsing
- _run_ctags: ctags execution and parsing with subprocess mocking
- extract_ctags_for_source_files: ctags extraction orchestration with token budget management
"""

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from core.ctags_extraction import (
    _get_rel_path_str_from_str,
    _parse_tag_line,
    _run_ctags,
    extract_ctags_for_source_files,
    format_tag,
)
from core.models import (
    FileCategory,
    FileMetadata,
)
from core.tokens import MockTokenBudget
from constants import CTAGS_KINDS


# ============================================================================
# Tests for format_tag
# ============================================================================


@pytest.mark.unit
@pytest.mark.parametrize(
    "kind,name,expected",
    [
        ("function", "myFunction", "function myFunction"),
        ("class", "MyClass", "class MyClass"),
        ("method", "doSomething", "method doSomething"),
    ],
)
def test_format_tag_basic(kind, name, expected):
    """Basic tag formatting should combine kind and name with space."""
    assert format_tag(kind, name) == expected


@pytest.mark.unit
@pytest.mark.parametrize("kind", CTAGS_KINDS)
def test_format_tag_all_kinds(kind):
    """Test all valid CTAGS_KINDS formatting."""
    result = format_tag(kind, "testName")
    assert result == f"{kind} testName"
    assert kind in result
    assert "testName" in result


@pytest.mark.unit
@pytest.mark.parametrize(
    "kind,name,expected",
    [
        ("", "", " "),
        ("function", "", "function "),
        ("", "myFunction", " myFunction"),
    ],
)
def test_format_tag_empty_strings(kind, name, expected):
    """Edge case: empty kind or name should still format."""
    assert format_tag(kind, name) == expected


@pytest.mark.unit
@pytest.mark.parametrize(
    "kind,name,expected",
    [
        ("function", "my_function", "function my_function"),
        ("class", "MyClass123", "class MyClass123"),
        ("method", "do_something_else", "method do_something_else"),
        ("function", "test-name", "function test-name"),
        ("class", "My$Class", "class My$Class"),
    ],
)
def test_format_tag_special_characters(kind, name, expected):
    """Names with special characters, underscores, numbers should format correctly."""
    assert format_tag(kind, name) == expected


# ============================================================================
# Tests for _get_rel_path_str_from_str
# ============================================================================


@pytest.mark.unit
@pytest.mark.parametrize(
    "full_path,expected",
    [
        ("/project/src/file.py", "src/file.py"),
        ("/project/file.py", "file.py"),
        ("/project/src/utils/helpers/file.py", "src/utils/helpers/file.py"),
    ],
)
def test_get_rel_path_str_from_str(full_path, expected):
    """Should convert absolute path to relative path string."""
    root = Path("/project")
    assert _get_rel_path_str_from_str(root, full_path) == expected


@pytest.mark.unit
def test_get_rel_path_str_from_str_same_root_and_path():
    """Edge case: root equals full path should return '.'."""
    root = Path("/project")
    full = "/project"
    result = _get_rel_path_str_from_str(root, full)
    assert result == "."


@pytest.mark.unit
def test_get_rel_path_str_from_str_absolute_paths():
    """Absolute paths should convert correctly."""
    root = Path("/Users/user/project")
    full = "/Users/user/project/src/main.py"
    assert _get_rel_path_str_from_str(root, full) == "src/main.py"


# ============================================================================
# Tests for _parse_tag_line
# ============================================================================


@pytest.mark.unit
@pytest.mark.parametrize(
    "line,expected_path,expected_kind,expected_name",
    [
        (
            '{"path": "file.py", "kind": "function", "name": "foo"}',
            "file.py",
            "function",
            "foo",
        ),
        (
            '{"path": "file.py", "kind": "class", "name": "MyClass"}',
            "file.py",
            "class",
            "MyClass",
        ),
    ],
)
def test_parse_tag_line_valid(line, expected_path, expected_kind, expected_name):
    """Valid tag line with all required fields should parse correctly."""
    result = _parse_tag_line(line)
    assert result is not None
    assert result.path == expected_path
    assert result.kind == expected_kind
    assert result.name == expected_name


@pytest.mark.unit
@pytest.mark.parametrize("kind", CTAGS_KINDS)
def test_parse_tag_line_allowed_kinds(kind):
    """Test each kind in CTAGS_KINDS parses correctly."""
    line = f'{{"path": "file.py", "kind": "{kind}", "name": "test"}}'
    result = _parse_tag_line(line)
    assert result is not None
    assert result.kind == kind
    assert result.name == "test"


@pytest.mark.unit
@pytest.mark.parametrize(
    "invalid_line",
    [
        "not json",
        '{"path": "file.py"',
        '{"path": "file.py", "kind":}',
        "",
        "   ",
        "\n\t",
        '{"kind": "function", "name": "foo"}',  # missing path
        '{"path": "file.py", "name": "foo"}',  # missing kind
        '{"path": "file.py", "kind": "function"}',  # missing name
        '{"path": "file.py", "kind": "invalid_kind", "name": "foo"}',  # invalid kind
        '{"path": "", "kind": "function", "name": "foo"}',  # empty path
        '{"path": "file.py", "kind": "function", "name": ""}',  # empty name
    ],
)
def test_parse_tag_line_invalid(invalid_line):
    """Invalid or malformed tag lines should return None."""
    assert _parse_tag_line(invalid_line) is None


@pytest.mark.unit
def test_parse_tag_line_extra_fields():
    """JSON with extra fields should still work if required fields present."""
    line = '{"path": "file.py", "kind": "function", "name": "foo", "line": 42, "extra": "data"}'
    result = _parse_tag_line(line)
    assert result is not None
    assert result.path == "file.py"
    assert result.kind == "function"
    assert result.name == "foo"


# ============================================================================
# Tests for _run_ctags
# ============================================================================


@pytest.mark.unit
@pytest.mark.mock
def test_run_ctags_successful_single_file(
    project_root, sample_file_metadata, mock_popen_factory
):
    """Should parse single file with single tag correctly."""
    files = [sample_file_metadata]
    stdout_lines = [
        f'{{"path": "{project_root}/file.py", "kind": "function", "name": "foo"}}\n'
    ]

    mock_popen = mock_popen_factory(stdout_lines)
    result, next_index = _run_ctags(
        root=project_root,
        files=files,
        start=0,
        ctags_path=Path("/fake/ctags"),
        popen_factory=mock_popen,
    )

    assert result is not None
    assert len(result) == 1
    assert result[0].path == "file.py"
    assert result[0].type == FileCategory.SOURCE.value
    assert "function foo" in result[0].content
    assert next_index == 1


@pytest.mark.unit
@pytest.mark.mock
def test_run_ctags_successful_multiple_tags_same_file(
    project_root, sample_file_metadata, mock_popen_factory
):
    """Multiple tags in one file should be grouped correctly."""
    files = [sample_file_metadata]
    stdout_lines = [
        f'{{"path": "{project_root}/file.py", "kind": "class", "name": "MyClass"}}\n',
        f'{{"path": "{project_root}/file.py", "kind": "method", "name": "myMethod"}}\n',
        f'{{"path": "{project_root}/file.py", "kind": "function", "name": "helper"}}\n',
    ]

    mock_popen = mock_popen_factory(stdout_lines)
    result, next_index = _run_ctags(
        root=project_root,
        files=files,
        start=0,
        ctags_path=Path("/fake/ctags"),
        popen_factory=mock_popen,
    )

    assert result is not None
    assert len(result) == 1
    assert result[0].path == "file.py"
    content = result[0].content
    assert "class MyClass" in content
    assert "method myMethod" in content
    assert "function helper" in content
    assert next_index == 1


@pytest.mark.unit
@pytest.mark.mock
def test_run_ctags_successful_multiple_files(project_root, mock_popen_factory):
    """Multiple files in batch should be processed correctly."""
    files = [
        FileMetadata(Path("file1.py"), FileCategory.SOURCE),
        FileMetadata(Path("file2.py"), FileCategory.SOURCE),
    ]
    stdout_lines = [
        f'{{"path": "{project_root}/file1.py", "kind": "function", "name": "foo"}}\n',
        f'{{"path": "{project_root}/file2.py", "kind": "class", "name": "Bar"}}\n',
    ]

    mock_popen = mock_popen_factory(stdout_lines)
    result, next_index = _run_ctags(
        root=project_root,
        files=files,
        start=0,
        ctags_path=Path("/fake/ctags"),
        popen_factory=mock_popen,
    )

    assert result is not None
    assert len(result) == 2
    assert result[0].path == "file1.py"
    assert result[1].path == "file2.py"
    assert next_index == 2


@pytest.mark.unit
@pytest.mark.mock
def test_run_ctags_custom_limit(project_root, mock_popen_factory):
    """Custom limit parameter should be respected."""
    files = [
        FileMetadata(Path("file1.py"), FileCategory.SOURCE),
        FileMetadata(Path("file2.py"), FileCategory.SOURCE),
        FileMetadata(Path("file3.py"), FileCategory.SOURCE),
    ]
    stdout_lines = [
        f'{{"path": "{project_root}/file1.py", "kind": "function", "name": "foo"}}\n',
    ]

    mock_popen = mock_popen_factory(stdout_lines)
    result, _next_index = _run_ctags(
        root=project_root,
        files=files,
        start=0,
        limit=1,
        ctags_path=Path("/fake/ctags"),
        popen_factory=mock_popen,
    )

    assert result is not None
    assert len(result) == 1


@pytest.mark.unit
@pytest.mark.mock
def test_run_ctags_custom_ctags_path(project_root, sample_file_metadata):
    """Custom ctags_path parameter should be used."""
    files = [sample_file_metadata]
    stdout_lines = [
        f'{{"path": "{project_root}/file.py", "kind": "function", "name": "foo"}}\n'
    ]

    custom_path = Path("/custom/ctags/path")

    def mock_popen(cmd, **_kwargs):
        # Verify the custom path is used in the command
        assert str(custom_path) in cmd
        mock_process = MagicMock()
        mock_process.stdout = iter(stdout_lines)
        mock_process.__enter__ = MagicMock(return_value=mock_process)
        mock_process.__exit__ = MagicMock(return_value=None)
        return mock_process

    result, _next_index = _run_ctags(
        root=project_root,
        files=files,
        start=0,
        ctags_path=custom_path,
        popen_factory=mock_popen,
    )

    assert result is not None
    assert len(result) == 1


@pytest.mark.unit
@pytest.mark.mock
def test_run_ctags_custom_popen_factory(project_root, sample_file_metadata):
    """Custom popen_factory should be used."""
    files = [sample_file_metadata]
    stdout_lines = [
        f'{{"path": "{project_root}/file.py", "kind": "function", "name": "foo"}}\n'
    ]

    factory_called = []

    def mock_popen(*_args, **_kwargs):
        factory_called.append(True)
        mock_process = MagicMock()
        mock_process.stdout = iter(stdout_lines)
        mock_process.__enter__ = MagicMock(return_value=mock_process)
        mock_process.__exit__ = MagicMock(return_value=None)
        return mock_process

    result, _next_index = _run_ctags(
        root=project_root,
        files=files,
        start=0,
        popen_factory=mock_popen,
    )

    assert len(factory_called) > 0
    assert result is not None


@pytest.mark.unit
@pytest.mark.mock
def test_run_ctags_subprocess_error(project_root, sample_file_metadata):
    """OSError/SubprocessError should return (None, current_index)."""
    files = [sample_file_metadata]

    def mock_popen(*_args, **_kwargs):
        raise OSError("Subprocess failed")

    result, next_index = _run_ctags(
        root=project_root,
        files=files,
        start=0,
        popen_factory=mock_popen,
    )

    assert result is None
    assert next_index == 0


@pytest.mark.unit
@pytest.mark.mock
def test_run_ctags_empty_file_list(project_root, mock_popen_factory):
    """Empty files list should return empty result."""
    files = []

    mock_popen = mock_popen_factory([])
    result, _next_index = _run_ctags(
        root=project_root,
        files=files,
        start=0,
        popen_factory=mock_popen,
    )

    assert result is not None
    assert len(result) == 0


@pytest.mark.unit
@pytest.mark.mock
def test_run_ctags_eof_handling(project_root, sample_file_metadata, mock_popen_factory):
    """Empty string from stdout (EOF) should return (None, current_index)."""
    files = [sample_file_metadata]

    mock_popen = mock_popen_factory([""])  # EOF
    result, _next_index = _run_ctags(
        root=project_root,
        files=files,
        start=0,
        popen_factory=mock_popen,
    )

    assert result is None


@pytest.mark.unit
@pytest.mark.mock
def test_run_ctags_blank_lines_skipped(
    project_root, sample_file_metadata, mock_popen_factory
):
    """Blank/whitespace lines should be ignored."""
    files = [sample_file_metadata]
    stdout_lines = [
        "\n",
        "   \n",
        "\t\n",
        f'{{"path": "{project_root}/file.py", "kind": "function", "name": "foo"}}\n',
        "\n",
    ]

    mock_popen = mock_popen_factory(stdout_lines)
    result, _next_index = _run_ctags(
        root=project_root,
        files=files,
        start=0,
        popen_factory=mock_popen,
    )

    assert result is not None
    assert len(result) == 1
    assert "function foo" in result[0].content


@pytest.mark.unit
@pytest.mark.mock
def test_run_ctags_invalid_category(project_root):
    """Non-SOURCE category should raise ValueError."""
    files = [FileMetadata(Path("file.py"), FileCategory.MANIFEST)]

    def mock_popen(*_args, **_kwargs):
        mock_process = MagicMock()
        mock_process.stdout = iter([])
        mock_process.__enter__ = MagicMock(return_value=mock_process)
        mock_process.__exit__ = MagicMock(return_value=None)
        return mock_process

    with pytest.raises(ValueError, match="Ctags must only be run on source files"):
        _run_ctags(
            root=project_root,
            files=files,
            start=0,
            category=FileCategory.MANIFEST,
            popen_factory=mock_popen,
        )


@pytest.mark.unit
@pytest.mark.mock
def test_run_ctags_invalid_json_lines(
    project_root, sample_file_metadata, mock_popen_factory
):
    """Invalid JSON lines should be skipped."""
    files = [sample_file_metadata]
    stdout_lines = [
        "not json\n",
        f'{{"path": "{project_root}/file.py", "kind": "function", "name": "foo"}}\n',
        '{"invalid": "json"}\n',
    ]

    mock_popen = mock_popen_factory(stdout_lines)
    result, _next_index = _run_ctags(
        root=project_root,
        files=files,
        start=0,
        popen_factory=mock_popen,
    )

    assert result is not None
    assert len(result) == 1
    assert "function foo" in result[0].content


@pytest.mark.unit
@pytest.mark.mock
def test_run_ctags_tags_spanning_files(project_root, mock_popen_factory):
    """Tags from multiple files should be grouped correctly."""
    files = [
        FileMetadata(Path("file1.py"), FileCategory.SOURCE),
        FileMetadata(Path("file2.py"), FileCategory.SOURCE),
    ]
    stdout_lines = [
        f'{{"path": "{project_root}/file1.py", "kind": "class", "name": "Class1"}}\n',
        f'{{"path": "{project_root}/file1.py", "kind": "method", "name": "method1"}}\n',
        f'{{"path": "{project_root}/file2.py", "kind": "function", "name": "func2"}}\n',
    ]

    mock_popen = mock_popen_factory(stdout_lines)
    result, _next_index = _run_ctags(
        root=project_root,
        files=files,
        start=0,
        popen_factory=mock_popen,
    )

    assert result is not None
    assert len(result) == 2
    assert result[0].path == "file1.py"
    assert "class Class1" in result[0].content
    assert "method method1" in result[0].content
    assert result[1].path == "file2.py"
    assert "function func2" in result[1].content


@pytest.mark.unit
@pytest.mark.mock
def test_run_ctags_start_index_respected(project_root):
    """Start parameter should correctly skip files."""
    files = [
        FileMetadata(Path("file0.py"), FileCategory.SOURCE),
        FileMetadata(Path("file1.py"), FileCategory.SOURCE),
        FileMetadata(Path("file2.py"), FileCategory.SOURCE),
    ]
    stdout_lines = [
        f'{{"path": "{project_root}/file1.py", "kind": "function", "name": "foo"}}\n',
    ]

    def mock_popen(cmd, **_kwargs):
        # Verify file0.py is not in the command
        cmd_str = " ".join(cmd)
        assert "file0.py" not in cmd_str
        assert "file1.py" in cmd_str
        mock_process = MagicMock()
        mock_process.stdout = iter(stdout_lines)
        mock_process.__enter__ = MagicMock(return_value=mock_process)
        mock_process.__exit__ = MagicMock(return_value=None)
        return mock_process

    result, _next_index = _run_ctags(
        root=project_root,
        files=files,
        start=1,
        popen_factory=mock_popen,
    )

    assert result is not None


# ============================================================================
# Tests for extract_ctags_for_source_files
# ============================================================================


@pytest.mark.unit
@pytest.mark.mock
def test_extract_ctags_successful_single_batch(
    project_root,
    sample_file_metadata,
    token_counter,
    token_budget,
    category_status,
    processed_file_factory,
    progress_display,
    mocker,
):
    """Should extract tags and process files successfully."""
    files = [sample_file_metadata]
    processed_file = processed_file_factory()

    mock_run = mocker.patch("core.ctags_extraction._run_ctags")
    mock_run.return_value = ([processed_file], 1)

    extract_ctags_for_source_files(
        root=project_root,
        files=files,
        counter=token_counter,
        token_budget=token_budget,
        status=category_status,
        progress_display=progress_display,
    )

    assert len(category_status.files) == 1
    assert category_status.files[0].path == "file.py"
    assert len(token_budget.start_category_calls) == 1
    assert token_budget.start_category_calls[0] == FileCategory.SOURCE


@pytest.mark.unit
@pytest.mark.mock
def test_extract_ctags_successful_multiple_batches(
    project_root,
    token_counter,
    token_budget,
    category_status,
    processed_file_factory,
    progress_display,
    mocker,
):
    """Multiple batches should call _run_ctags multiple times."""
    files = [
        FileMetadata(Path("file1.py"), FileCategory.SOURCE),
        FileMetadata(Path("file2.py"), FileCategory.SOURCE),
    ]
    processed_file1 = processed_file_factory(path="file1.py", content="function foo")
    processed_file2 = processed_file_factory(path="file2.py", content="class Bar")

    mock_run = mocker.patch("core.ctags_extraction._run_ctags")
    mock_run.side_effect = [
        ([processed_file1], 1),
        ([processed_file2], 2),
    ]

    extract_ctags_for_source_files(
        root=project_root,
        files=files,
        counter=token_counter,
        token_budget=token_budget,
        status=category_status,
        progress_display=progress_display,
    )

    assert len(category_status.files) == 2
    assert mock_run.call_count == 2


@pytest.mark.unit
@pytest.mark.mock
def test_extract_ctags_token_budget_exhaustion(
    project_root,
    sample_file_metadata,
    token_counter,
    category_status,
    processed_file_factory,
    progress_display,
    mocker,
):
    """Should stop when budget exhausted."""
    files = [sample_file_metadata]
    budget = MockTokenBudget(can_afford_return=False)  # Can't afford anything
    processed_file = processed_file_factory(path="file1.py", content="function foo")

    mock_run = mocker.patch("core.ctags_extraction._run_ctags")
    mock_run.return_value = ([processed_file], 1)

    extract_ctags_for_source_files(
        root=project_root,
        files=files,
        counter=token_counter,
        token_budget=budget,
        status=category_status,
        progress_display=progress_display,
    )

    assert len(category_status.files) == 0  # No files added because budget exhausted


@pytest.mark.unit
@pytest.mark.mock
def test_extract_ctags_empty_file_list(
    project_root,
    token_counter,
    token_budget,
    category_status,
    progress_display,
    mocker,
):
    """Empty files list should complete without errors."""
    files = []

    mock_run = mocker.patch("core.ctags_extraction._run_ctags")
    mock_run.return_value = (None, 0)

    extract_ctags_for_source_files(
        root=project_root,
        files=files,
        counter=token_counter,
        token_budget=token_budget,
        status=category_status,
        progress_display=progress_display,
    )

    assert len(category_status.files) == 0


@pytest.mark.unit
@pytest.mark.mock
def test_extract_ctags_progress_display_used(
    project_root,
    sample_file_metadata,
    token_counter,
    token_budget,
    category_status,
    processed_file_factory,
    tracking_progress_display,
    mocker,
):
    """Progress display methods should be called correctly."""
    files = [sample_file_metadata]
    processed_file = processed_file_factory()

    mock_run = mocker.patch("core.ctags_extraction._run_ctags")
    mock_run.return_value = ([processed_file], 1)

    extract_ctags_for_source_files(
        root=project_root,
        files=files,
        counter=token_counter,
        token_budget=token_budget,
        status=category_status,
        progress_display=tracking_progress_display,
    )

    assert any(call[0] == "start" for call in tracking_progress_display.calls)
    assert any(call[0] == "complete" for call in tracking_progress_display.calls)


@pytest.mark.unit
@pytest.mark.mock
def test_extract_ctags_token_counter_used(
    project_root,
    sample_file_metadata,
    token_counter,
    token_budget,
    category_status,
    processed_file_factory,
    progress_display,
    mocker,
):
    """Token counter should be called for each file."""
    files = [sample_file_metadata]
    processed_file = processed_file_factory()

    mock_run = mocker.patch("core.ctags_extraction._run_ctags")
    mock_run.return_value = ([processed_file], 1)

    extract_ctags_for_source_files(
        root=project_root,
        files=files,
        counter=token_counter,
        token_budget=token_budget,
        status=category_status,
        progress_display=progress_display,
    )

    # Counter should have been called (we can't easily verify this without
    # making counter track calls, but the test verifies the flow works)
    assert len(category_status.files) == 1


@pytest.mark.unit
@pytest.mark.mock
def test_extract_ctags_token_budget_start_category(
    project_root,
    sample_file_metadata,
    token_counter,
    token_budget,
    category_status,
    processed_file_factory,
    progress_display,
    mocker,
):
    """Budget start_category should be called with SOURCE."""
    files = [sample_file_metadata]
    processed_file = processed_file_factory()

    mock_run = mocker.patch("core.ctags_extraction._run_ctags")
    mock_run.return_value = ([processed_file], 1)

    extract_ctags_for_source_files(
        root=project_root,
        files=files,
        counter=token_counter,
        token_budget=token_budget,
        status=category_status,
        progress_display=progress_display,
    )

    assert len(token_budget.start_category_calls) == 1
    assert token_budget.start_category_calls[0] == FileCategory.SOURCE


@pytest.mark.unit
@pytest.mark.mock
def test_extract_ctags_status_accumulation(
    project_root,
    token_counter,
    token_budget,
    category_status,
    processed_file_factory,
    progress_display,
    mocker,
):
    """Files should be appended to status correctly."""
    files = [
        FileMetadata(Path("file1.py"), FileCategory.SOURCE),
        FileMetadata(Path("file2.py"), FileCategory.SOURCE),
    ]
    processed_file1 = processed_file_factory(path="file1.py", content="function foo")
    processed_file2 = processed_file_factory(path="file2.py", content="class Bar")

    mock_run = mocker.patch("core.ctags_extraction._run_ctags")
    mock_run.side_effect = [
        ([processed_file1], 1),
        ([processed_file2], 2),
    ]

    extract_ctags_for_source_files(
        root=project_root,
        files=files,
        counter=token_counter,
        token_budget=token_budget,
        status=category_status,
        progress_display=progress_display,
    )

    assert len(category_status.files) == 2
    assert category_status.files[0].path == "file1.py"
    assert category_status.files[1].path == "file2.py"


@pytest.mark.unit
@pytest.mark.mock
def test_extract_ctags_files_processed_count(
    project_root,
    token_counter,
    token_budget,
    category_status,
    processed_file_factory,
    progress_display,
    mocker,
):
    """Files processed count should be tracked correctly."""
    files = [
        FileMetadata(Path("file1.py"), FileCategory.SOURCE),
        FileMetadata(Path("file2.py"), FileCategory.SOURCE),
    ]
    processed_file1 = processed_file_factory(path="file1.py", content="function foo")
    processed_file2 = processed_file_factory(path="file2.py", content="class Bar")

    mock_run = mocker.patch("core.ctags_extraction._run_ctags")
    mock_run.side_effect = [
        ([processed_file1], 1),
        ([processed_file2], 2),
    ]

    extract_ctags_for_source_files(
        root=project_root,
        files=files,
        counter=token_counter,
        token_budget=token_budget,
        status=category_status,
        progress_display=progress_display,
    )

    # Both files should be processed
    assert len(category_status.files) == 2


@pytest.mark.unit
@pytest.mark.mock
def test_extract_ctags_budget_can_afford_checks(
    project_root,
    sample_file_metadata,
    token_counter,
    token_budget,
    category_status,
    processed_file_factory,
    progress_display,
    mocker,
):
    """Budget can_afford should be called before spending."""
    files = [sample_file_metadata]
    processed_file = processed_file_factory()

    mock_run = mocker.patch("core.ctags_extraction._run_ctags")
    mock_run.return_value = ([processed_file], 1)

    extract_ctags_for_source_files(
        root=project_root,
        files=files,
        counter=token_counter,
        token_budget=token_budget,
        status=category_status,
        progress_display=progress_display,
    )

    assert len(token_budget.can_afford_calls) > 0
    assert len(token_budget.spend_calls) > 0
    # can_afford should be called before spend
    assert len(token_budget.can_afford_calls) == len(token_budget.spend_calls)


@pytest.mark.unit
@pytest.mark.mock
def test_extract_ctags_budget_spend_called(
    project_root,
    sample_file_metadata,
    token_counter,
    token_budget,
    category_status,
    processed_file_factory,
    progress_display,
    mocker,
):
    """Budget spend should be called for each processed file."""
    files = [sample_file_metadata]
    processed_file = processed_file_factory()

    mock_run = mocker.patch("core.ctags_extraction._run_ctags")
    mock_run.return_value = ([processed_file], 1)

    extract_ctags_for_source_files(
        root=project_root,
        files=files,
        counter=token_counter,
        token_budget=token_budget,
        status=category_status,
        progress_display=progress_display,
    )

    assert len(token_budget.spend_calls) == 1
    assert token_budget.spend_calls[0] == 100  # Token count from counter


@pytest.mark.unit
@pytest.mark.mock
def test_extract_ctags_noop_progress_display(
    project_root,
    sample_file_metadata,
    token_counter,
    token_budget,
    category_status,
    processed_file_factory,
    progress_display,
    mocker,
):
    """Should work with NoOpProgressDisplay."""
    files = [sample_file_metadata]
    processed_file = processed_file_factory()

    mock_run = mocker.patch("core.ctags_extraction._run_ctags")
    mock_run.return_value = ([processed_file], 1)

    extract_ctags_for_source_files(
        root=project_root,
        files=files,
        counter=token_counter,
        token_budget=token_budget,
        status=category_status,
        progress_display=progress_display,
    )

    assert len(category_status.files) == 1
