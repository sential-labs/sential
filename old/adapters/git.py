"""
Git repository adapter for file discovery operations.

This module provides a high-level interface for interacting with Git repositories
to discover and enumerate files. It abstracts subprocess calls to git commands
and provides streaming generators for memory-efficient file path enumeration.
"""

from pathlib import Path
import subprocess
from typing import Protocol


class GitClient(Protocol):
    """
    Protocol defining the interface for Git repository clients.

    This protocol specifies the required methods that any Git client implementation
    must provide for repository discovery and file enumeration operations.
    """

    def is_repo(self) -> bool:
        """Check if path is a Git repository."""

    def count_files(self) -> int:
        """Count files in repository."""

    def get_file_paths_list(self) -> list[Path]:
        """Get list of file paths."""


class SubprocessGitClient:
    """
    Client for interacting with Git repositories.

    This class provides methods to query Git repositories for file information,
    check repository status, and stream file paths efficiently. It encapsulates
    all Git subprocess operations and provides a clean interface for the discovery
    pipeline.

    Attributes:
        root: The root path of the Git repository this client operates on.
    """

    def __init__(self, root: Path):
        """
        Initialize a GitClient for the specified repository root.

        Args:
            root: The root directory path of the Git repository.
        """
        self.root = root
        self.cmd = ["git", "ls-files", "--cached", "--others", "--exclude-standard"]

    def is_repo(self) -> bool:
        """
        Check if the root path is a valid Git repository.

        This method verifies that the root directory is inside a Git working tree
        by executing `git rev-parse --is-inside-work-tree`. This is a lightweight
        check that doesn't require reading the entire repository structure.

        Returns:
            bool: True if the root is a valid Git repository, False otherwise.
        """
        try:
            subprocess.run(
                ["git", "rev-parse", "--is-inside-work-tree"],
                cwd=self.root,
                text=True,
                check=True,  # This triggers except block
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return True
        except subprocess.CalledProcessError:
            return False

    def count_files(self) -> int:
        """
        Efficiently counts the number of files in the Git repository.

        This method executes `git ls-files` and streams the output to count newlines
        without loading the entire output into memory. This is used to calculate totals
        for progress bars before processing begins.

        Returns:
            int: The total number of files returned by the git ls-files command.
        """

        # Construct the command: git ls-files ... -- path1 path2
        # The "--" separator tells git "everything after this is a path"

        count = 0
        # Use Popen to open a pipe, not a buffer
        with self._create_subprocess(self.cmd) as process:

            # Iterate over the stream directly
            if process.stdout:
                for _ in process.stdout:
                    count += 1

        return count

    def get_file_paths_list(self) -> list[Path]:
        """
        Return all relevant file paths from the Git index and working tree.

        This method executes `git ls-files` to retrieve a list of files that are either
        cached (tracked) or untracked but not ignored (respecting `.gitignore`).
        It uses a subprocess pipe to read results line-by-line.

        Returns:
            list[Path]: A list of relative path objects (relative to repository root)
                for each file found in the repository.
        """
        file_paths: list[Path] = []

        with self._create_subprocess(self.cmd) as process:
            if process.stdout:
                for p in process.stdout:
                    file_paths.append(Path(p.strip()))

            process.wait()

        return file_paths

    def _create_subprocess(self, cmd: list[str]) -> subprocess.Popen[str]:
        """
        Create a subprocess for executing Git commands with streaming output.

        This helper method creates a subprocess configured for line-buffered text output,
        allowing efficient streaming of command results without loading everything into
        memory at once.

        Args:
            cmd: The command to execute as a list of strings.

        Returns:
            subprocess.Popen[str]: A subprocess object with stdout configured as a pipe
                for streaming, stderr suppressed, and line-buffered text mode enabled.
        """
        return subprocess.Popen(
            cmd,
            cwd=self.root,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            bufsize=1,
        )


class MockGitClient:
    """
    Mock implementation of GitClient for testing.

    Provides configurable behavior for Git operations without requiring
    actual Git repositories or subprocess execution. Tracks method calls
    for test verification.
    """

    def __init__(
        self,
        is_repo_return: bool = True,
        count_files_return: int = 0,
        file_paths_list_return: list[Path] | None = None,
    ):
        """
        Initialize MockGitClient with configurable behavior.

        Args:
            is_repo_return: Return value for is_repo() calls. Defaults to True.
            count_files_return: Return value for count_files() calls. Defaults to 0.
            file_paths_list_return: Return value for get_file_paths_list() calls.
                If None, defaults to empty list.

        Attributes (for test inspection):
            is_repo_calls: Number of times is_repo() was called.
            count_files_calls: Number of times count_files() was called.
            get_file_paths_list_calls: Number of times get_file_paths_list() was called.
        """
        self.is_repo_return = is_repo_return
        self.count_files_return = count_files_return
        self.file_paths_list_return = file_paths_list_return or []

        # Track calls for test inspection
        self.is_repo_calls: int = 0
        self.count_files_calls: int = 0
        self.get_file_paths_list_calls: int = 0

    def is_repo(self) -> bool:
        """Check if path is a Git repository (tracks call, returns configured value)."""
        self.is_repo_calls += 1
        return self.is_repo_return

    def count_files(self) -> int:
        """Count files in repository (tracks call, returns configured value)."""
        self.count_files_calls += 1
        return self.count_files_return

    def get_file_paths_list(self) -> list[Path]:
        """Get list of file paths (tracks call, returns configured value)."""
        self.get_file_paths_list_calls += 1
        return self.file_paths_list_return
