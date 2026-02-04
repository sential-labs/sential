"""
Comprehensive tests for the git adapter module using pytest.

Tests cover:
- SubprocessGitClient: Git repository operations with subprocess mocking

TESTABILITY ANALYSIS:
====================

Current Implementation Issues:
-------------------------------
SubprocessGitClient currently uses hardcoded subprocess calls:
1. `is_repo()` directly calls `subprocess.run()` - no dependency injection
2. `_create_subprocess()` directly calls `subprocess.Popen()` - no dependency injection

This makes testing possible but requires mocking at the module level, which is less
clean than dependency injection.

Recommended Changes for Better Testability:
-------------------------------------------
Following the pattern used in `core/ctags_extraction.py` with `popen_factory`:

1. Modify `is_repo()` to accept optional `subprocess_run_factory` parameter:
   ```python
   def is_repo(self, subprocess_run_factory: Callable | None = None) -> bool:
       run = subprocess_run_factory if subprocess_run_factory else subprocess.run
       try:
           run([...], ...)
           return True
       except subprocess.CalledProcessError:
           return False
   ```

2. Modify `_create_subprocess()` to accept optional `popen_factory` parameter:
   ```python
   def _create_subprocess(
       self,
       cmd: list[str],
       popen_factory: Callable | None = None
   ) -> subprocess.Popen[str]:
       popen = popen_factory if popen_factory else subprocess.Popen
       return popen(cmd, cwd=self.root, ...)
   ```

3. Update `count_files()` and `get_file_paths_list()` to pass through the factory:
   ```python
   def count_files(self, popen_factory: Callable | None = None) -> int:
       with self._create_subprocess(self.cmd, popen_factory=popen_factory) as process:
           ...
   ```

Benefits:
- Tests can inject mock factories directly
- No need to patch at module level
- More explicit dependencies
- Follows established patterns in codebase (see test_ctags_extraction.py)

Current Tests:
--------------
The tests below work with the current implementation by mocking at the module level,
but would be cleaner with dependency injection as described above.
"""

from pathlib import Path
from unittest.mock import MagicMock
import subprocess

import pytest

from adapters.git import SubprocessGitClient


# ============================================================================
# Tests for SubprocessGitClient.__init__
# ============================================================================


@pytest.mark.unit
def test_subprocess_git_client_init():
    """SubprocessGitClient should initialize with root path and default command."""
    root = Path("/some/repo")
    client = SubprocessGitClient(root)

    assert client.root == root
    assert client.cmd == [
        "git",
        "ls-files",
        "--cached",
        "--others",
        "--exclude-standard",
    ]


# ============================================================================
# Tests for SubprocessGitClient.is_repo
# ============================================================================


@pytest.mark.unit
@pytest.mark.mock
def test_is_repo_returns_true_when_git_succeeds(mocker):
    """is_repo should return True when git rev-parse succeeds."""
    root = Path("/some/repo")
    client = SubprocessGitClient(root)

    # Mock subprocess.run to succeed (return code 0)
    mock_run = mocker.patch("adapters.git.subprocess.run")
    mock_run.return_value = MagicMock(returncode=0)

    result = client.is_repo()

    assert result is True
    mock_run.assert_called_once()
    call_args = mock_run.call_args
    assert call_args[0][0] == ["git", "rev-parse", "--is-inside-work-tree"]
    assert call_args[1]["cwd"] == root
    assert call_args[1]["check"] is True


@pytest.mark.unit
@pytest.mark.mock
def test_is_repo_returns_false_on_called_process_error(mocker):
    """is_repo should return False when git rev-parse fails."""
    root = Path("/some/repo")
    client = SubprocessGitClient(root)

    # Mock subprocess.run to raise CalledProcessError
    mock_run = mocker.patch("adapters.git.subprocess.run")
    mock_run.side_effect = subprocess.CalledProcessError(1, "git")

    result = client.is_repo()

    assert result is False
    mock_run.assert_called_once()


@pytest.mark.unit
@pytest.mark.mock
def test_is_repo_uses_correct_git_command(mocker):
    """is_repo should call git rev-parse with correct arguments."""
    root = Path("/some/repo")
    client = SubprocessGitClient(root)

    mock_run = mocker.patch("adapters.git.subprocess.run")
    mock_run.return_value = MagicMock(returncode=0)

    client.is_repo()

    call_args = mock_run.call_args
    assert call_args[0][0] == ["git", "rev-parse", "--is-inside-work-tree"]
    assert call_args[1]["stdout"] == subprocess.DEVNULL
    assert call_args[1]["stderr"] == subprocess.DEVNULL
    assert call_args[1]["text"] is True


# ============================================================================
# Tests for SubprocessGitClient.count_files
# ============================================================================


@pytest.mark.unit
@pytest.mark.mock
def test_count_files_counts_lines_from_stdout(mocker):
    """count_files should count lines from git ls-files output."""
    root = Path("/some/repo")
    client = SubprocessGitClient(root)

    # Mock _create_subprocess to return a mock process with stdout
    mock_process = MagicMock()
    mock_process.stdout = iter(["file1.py\n", "file2.py\n", "file3.py\n"])
    mock_process.__enter__ = MagicMock(return_value=mock_process)
    mock_process.__exit__ = MagicMock(return_value=None)

    mock_popen = mocker.patch("adapters.git.subprocess.Popen")
    mock_popen.return_value = mock_process

    result = client.count_files()

    assert result == 3
    mock_popen.assert_called_once()
    call_args = mock_popen.call_args
    assert call_args[0][0] == client.cmd
    assert call_args[1]["cwd"] == root


@pytest.mark.unit
@pytest.mark.mock
def test_count_files_handles_empty_output(mocker):
    """count_files should return 0 when no files are found."""
    root = Path("/some/repo")
    client = SubprocessGitClient(root)

    mock_process = MagicMock()
    mock_process.stdout = iter([])
    mock_process.__enter__ = MagicMock(return_value=mock_process)
    mock_process.__exit__ = MagicMock(return_value=None)

    mock_popen = mocker.patch("adapters.git.subprocess.Popen")
    mock_popen.return_value = mock_process

    result = client.count_files()

    assert result == 0


@pytest.mark.unit
@pytest.mark.mock
def test_count_files_handles_none_stdout(mocker):
    """count_files should handle None stdout gracefully."""
    root = Path("/some/repo")
    client = SubprocessGitClient(root)

    mock_process = MagicMock()
    mock_process.stdout = None
    mock_process.__enter__ = MagicMock(return_value=mock_process)
    mock_process.__exit__ = MagicMock(return_value=None)

    mock_popen = mocker.patch("adapters.git.subprocess.Popen")
    mock_popen.return_value = mock_process

    result = client.count_files()

    assert result == 0


# ============================================================================
# Tests for SubprocessGitClient.get_file_paths_list
# ============================================================================


@pytest.mark.unit
@pytest.mark.mock
def test_get_file_paths_list_returns_paths_from_stdout(mocker):
    """get_file_paths_list should return list of Path objects from git output."""
    root = Path("/some/repo")
    client = SubprocessGitClient(root)

    # Mock process with file paths
    mock_process = MagicMock()
    mock_process.stdout = iter(["file1.py\n", "file2.py\n", "src/file3.py\n"])
    mock_process.__enter__ = MagicMock(return_value=mock_process)
    mock_process.__exit__ = MagicMock(return_value=None)
    mock_process.wait = MagicMock()

    mock_popen = mocker.patch("adapters.git.subprocess.Popen")
    mock_popen.return_value = mock_process

    result = client.get_file_paths_list()

    assert len(result) == 3
    assert result[0] == Path("file1.py")
    assert result[1] == Path("file2.py")
    assert result[2] == Path("src/file3.py")
    mock_process.wait.assert_called_once()


@pytest.mark.unit
@pytest.mark.mock
def test_get_file_paths_list_strips_whitespace(mocker):
    """get_file_paths_list should strip whitespace from paths."""
    root = Path("/some/repo")
    client = SubprocessGitClient(root)

    mock_process = MagicMock()
    mock_process.stdout = iter(["  file1.py  \n", "\tfile2.py\t\n"])
    mock_process.__enter__ = MagicMock(return_value=mock_process)
    mock_process.__exit__ = MagicMock(return_value=None)
    mock_process.wait = MagicMock()

    mock_popen = mocker.patch("adapters.git.subprocess.Popen")
    mock_popen.return_value = mock_process

    result = client.get_file_paths_list()

    assert result[0] == Path("file1.py")
    assert result[1] == Path("file2.py")


@pytest.mark.unit
@pytest.mark.mock
def test_get_file_paths_list_handles_empty_output(mocker):
    """get_file_paths_list should return empty list when no files found."""
    root = Path("/some/repo")
    client = SubprocessGitClient(root)

    mock_process = MagicMock()
    mock_process.stdout = iter([])
    mock_process.__enter__ = MagicMock(return_value=mock_process)
    mock_process.__exit__ = MagicMock(return_value=None)
    mock_process.wait = MagicMock()

    mock_popen = mocker.patch("adapters.git.subprocess.Popen")
    mock_popen.return_value = mock_process

    result = client.get_file_paths_list()

    assert result == []
    mock_process.wait.assert_called_once()


@pytest.mark.unit
@pytest.mark.mock
def test_get_file_paths_list_handles_none_stdout(mocker):
    """get_file_paths_list should handle None stdout gracefully."""
    root = Path("/some/repo")
    client = SubprocessGitClient(root)

    mock_process = MagicMock()
    mock_process.stdout = None
    mock_process.__enter__ = MagicMock(return_value=mock_process)
    mock_process.__exit__ = MagicMock(return_value=None)
    mock_process.wait = MagicMock()

    mock_popen = mocker.patch("adapters.git.subprocess.Popen")
    mock_popen.return_value = mock_process

    result = client.get_file_paths_list()

    assert result == []
    mock_process.wait.assert_called_once()


# ============================================================================
# Tests for SubprocessGitClient._create_subprocess
# ============================================================================


@pytest.mark.unit
@pytest.mark.mock
def test_create_subprocess_configures_popen_correctly(mocker):
    """_create_subprocess should configure Popen with correct parameters."""
    root = Path("/some/repo")
    client = SubprocessGitClient(root)
    cmd = ["git", "ls-files"]

    mock_popen = mocker.patch("adapters.git.subprocess.Popen")
    mock_process = MagicMock()
    mock_popen.return_value = mock_process

    result = client._create_subprocess(cmd)

    assert result == mock_process
    mock_popen.assert_called_once_with(
        cmd,
        cwd=root,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        bufsize=1,
    )


@pytest.mark.unit
@pytest.mark.mock
def test_create_subprocess_uses_client_root(mocker):
    """_create_subprocess should use client's root as cwd."""
    root = Path("/custom/repo/path")
    client = SubprocessGitClient(root)

    mock_popen = mocker.patch("adapters.git.subprocess.Popen")
    mock_popen.return_value = MagicMock()

    client._create_subprocess(["git", "ls-files"])

    call_kwargs = mock_popen.call_args[1]
    assert call_kwargs["cwd"] == root


# ============================================================================
# Integration-style tests
# ============================================================================


@pytest.mark.unit
@pytest.mark.mock
def test_count_files_and_get_file_paths_list_consistency(mocker):
    """count_files and get_file_paths_list should use same command."""
    root = Path("/some/repo")
    client = SubprocessGitClient(root)

    # Both should use client.cmd
    assert client.cmd == [
        "git",
        "ls-files",
        "--cached",
        "--others",
        "--exclude-standard",
    ]

    # Create a factory function that returns a new mock process each time
    # This ensures each call gets a fresh iterator
    def create_mock_process(*_args, **_kwargs):
        mock_process = MagicMock()
        mock_process.stdout = iter(["file1.py\n", "file2.py\n"])
        mock_process.__enter__ = MagicMock(return_value=mock_process)
        mock_process.__exit__ = MagicMock(return_value=None)
        mock_process.wait = MagicMock()
        return mock_process

    mock_popen = mocker.patch("adapters.git.subprocess.Popen")
    mock_popen.side_effect = create_mock_process

    count = client.count_files()
    paths = client.get_file_paths_list()

    # Both should have been called with the same command
    assert mock_popen.call_count == 2
    assert mock_popen.call_args_list[0][0][0] == client.cmd
    assert mock_popen.call_args_list[1][0][0] == client.cmd
    assert count == 2
    assert len(paths) == 2
