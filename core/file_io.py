from dataclasses import asdict
import json
import os
from pathlib import Path
import tempfile
from typing import Callable, Protocol

from core.exceptions import (
    FileDiscardError,
    FileReadError,
    FileWriteError,
    InvalidFilePathError,
    TempFileCreationError,
)
from core.models import CategoryProcessedFiles, FileCategory


class FileReader(Protocol):
    """
    Protocol defining the interface for file reading operations.

    This protocol specifies methods for reading files, allowing different
    implementations for production (filesystem) and testing (mocks).
    """

    def read_file(self, file_path: Path) -> str:
        """
        Read the text content of a file as UTF-8.

        Binary files and non-existent files are skipped. Invalid UTF-8 characters are
        silently ignored (errors="ignore"). Other I/O errors return an empty string.

        Args:
            file_path: The path to the file to read.

        Returns:
            The file content as a string, or an empty string if the file doesn't exist,
            is binary, or an I/O error occurs.
        """


class FileWriter(Protocol):
    """
    Protocol defining the interface for file writing operations.

    This protocol specifies methods for writing data to files, allowing different
    implementations for production (filesystem) and testing (mocks).
    """

    def write_file(self, data: str, mode: str = "w") -> None:
        """
        Write data to a file.

        Args:
            data: String data to write.
            mode: File mode ("w" for write/truncate, "a" for append). Defaults to "w".
        """

    def append_jsonl_line(self, data: dict) -> None:
        """
        Append a JSON line to a file.

        Args:
            data: Dictionary to serialize as JSON and append.
        """

    def append_processed_files(
        self, results: dict[FileCategory, CategoryProcessedFiles], mode: str = "a"
    ) -> None:
        """
        Append processed files to a file in JSONL format.

        Args:
            results: Dictionary mapping file categories to CategoryProcessedFiles.
            mode: File mode ("w" for write/truncate, "a" for append). Defaults to "a".
        """


class FilesystemFileReader:

    def read_file(self, file_path: Path) -> str:
        """
        Read the text content of a file as UTF-8.

        Binary files and non-existent files are skipped. Invalid UTF-8 characters are
        silently ignored (errors="ignore"). I/O errors raise FileReadError.

        Args:
            file_path: The path to the file to read.

        Returns:
            The file content as a string, or an empty string if the file doesn't exist
            or is binary.

        Raises:
            FileReadError: If an I/O error occurs while reading the file.
        """

        if not file_path.is_file():
            return ""

        # We skip binary files
        if self._is_binary_file(file_path):
            return ""

        try:
            with file_path.open("r", encoding="utf-8", errors="ignore") as f:
                content = f.read()

                return content
        except OSError as e:
            raise FileReadError(
                message=f"Failed to read file: {file_path}",
                file_path=str(file_path),
                original_exception=e,
            ) from e

    def _is_binary_file(self, file_path: Path) -> bool:
        """
        Determine if a file is binary by checking for null bytes.

        This function performs a fast heuristic check by reading the first 1024 bytes
        of the file and looking for null bytes (which are common in binary formats).
        Files with invalid UTF-8 are not considered binary since they can be read
        with errors="ignore" in read_file.

        Args:
            file_path: The path to the file to check.

        Returns:
            bool: True if the file appears to be binary (contains null bytes),
                False if it's likely text. Also returns True if the file cannot be read.
        """
        try:
            with open(file_path, "rb") as f:
                chunk = f.read(1024)
                if b"\0" in chunk:
                    return True
                return False
        except OSError:
            return True


class FilesystemFileWriter:
    def __init__(self, file_path: Path | None = None):
        self.file_path = file_path

    @classmethod
    def from_path(cls, file_path: Path) -> "FilesystemFileWriter":
        """
        Create a writer instance with an explicit file path.

        Args:
            file_path: The path to the file to manage.

        Returns:
            FilesystemFileWriter instance configured for the given path.

        Raises:
            InvalidFilePathError: If file_path is invalid (e.g., parent directory
                doesn't exist or is not writable).
        """
        parent = file_path.parent
        if not parent.exists():
            raise InvalidFilePathError(
                message=f"Parent directory does not exist: {parent}",
                file_path=str(file_path),
            )
        if not os.access(parent, os.W_OK):
            raise InvalidFilePathError(
                message=f"Parent directory is not writable: {parent}",
                file_path=str(file_path),
            )

        instance = cls()
        instance.file_path = file_path
        return instance

    @classmethod
    def from_tempfile(cls, suffix: str = ".jsonl") -> "FilesystemFileWriter":
        """
        Create a writer instance with a randomly-named tempfile.

        Args:
            suffix: File suffix (default: ".jsonl").

        Returns:
            FilesystemFileWriter instance with a unique tempfile path.

        Raises:
            TempFileCreationError: If tempfile cannot be created (disk full, permissions, etc.).
        """
        try:
            fd, file_path = tempfile.mkstemp(suffix=suffix)
            os.close(fd)
            instance = cls()
            instance.file_path = Path(file_path)
            return instance
        except OSError as e:
            raise TempFileCreationError(original_exception=e) from e

    @classmethod
    def from_named_tempfile(
        cls, name: str, suffix: str = ".jsonl"
    ) -> "FilesystemFileWriter":
        """
        Create a writer instance with a named tempfile in the system temp directory.

        Args:
            name: Base name for the tempfile (without suffix).
            suffix: File suffix (default: ".jsonl").

        Returns:
            FilesystemFileWriter instance with the named tempfile path.

        Raises:
            TempFileCreationError: If temp directory is not accessible or writable.
        """
        try:
            temp_dir = Path(tempfile.gettempdir())
            if not os.access(temp_dir, os.W_OK):
                raise TempFileCreationError(
                    message=f"Temp directory is not writable: {temp_dir}",
                    original_exception=OSError(
                        f"Temp directory is not writable: {temp_dir}"
                    ),
                )

            file_path = temp_dir / f"{name}{suffix}"
            instance = cls()
            instance.file_path = file_path
            return instance
        except OSError as e:
            raise TempFileCreationError(
                message=f"Failed to create named tempfile '{name}'",
                original_exception=e,
            ) from e

    def write_file(self, data: str, mode: str = "w") -> None:
        """
        Writes data to the output file.

        Args:
            data: String data to write
            mode: File mode ("w" for write/truncate, "a" for append)

        Raises:
            InvalidFilePathError: If file path is not set.
            FileWriteError: If writing to the file fails.
        """
        if self.file_path is None:
            raise InvalidFilePathError("No file path set. Use a factory method first.")

        try:
            with open(self.file_path, mode, encoding="utf-8") as f:
                f.write(data)
        except OSError as e:
            raise FileWriteError(
                message=f"Failed to write to file: {self.file_path}",
                file_path=str(self.file_path),
                original_exception=e,
            ) from e

    def append_jsonl_line(self, data: dict) -> None:
        """
        Appends a JSON line to the output file.

        Args:
            data: Dictionary to serialize as JSON and append.

        Raises:
            InvalidFilePathError: If file path is not set.
            FileWriteError: If writing to the file fails.
        """
        if self.file_path is None:
            raise InvalidFilePathError("No file path set. Use a factory method first.")

        try:
            with open(self.file_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(data) + "\n")
        except OSError as e:
            raise FileWriteError(
                message=f"Failed to append JSON line to file: {self.file_path}",
                file_path=str(self.file_path),
                original_exception=e,
            ) from e

    def append_processed_files(
        self, results: dict[FileCategory, CategoryProcessedFiles], mode: str = "a"
    ) -> None:
        """
        Writes processed files to the output file in JSONL format.

        Creates JSON records for each processed file and writes them as lines
        to the output file.

        Args:
            results: Dictionary mapping file categories to CategoryProcessedFiles.
            mode: File mode ("w" for write/truncate, "a" for append). Defaults to "a".

        Raises:
            InvalidFilePathError: If file path is not set.
            FileWriteError: If writing to the file fails.
        """
        if self.file_path is None:
            raise InvalidFilePathError("No file path set. Use a factory method first.")

        try:
            with open(self.file_path, mode, encoding="utf-8") as out_f:
                for _, status in results.items():
                    for processed_file in status.files:
                        out_f.write(json.dumps(asdict(processed_file)) + "\n")
        except OSError as e:
            raise FileWriteError(
                message=f"Failed to append processed files to file: {self.file_path}",
                file_path=str(self.file_path),
                original_exception=e,
            ) from e

    def discard(self) -> None:
        """
        Delete the file managed by this instance.

        Raises:
            InvalidFilePathError: If file path is not set.
            FileDiscardError: If the file cannot be deleted (doesn't exist, locked, etc.).
        """
        if self.file_path is None:
            raise InvalidFilePathError("No file path set. Use a factory method first.")

        try:
            self.file_path.unlink()
        except FileNotFoundError as e:
            raise FileDiscardError(
                message=f"Cannot discard file since it no longer exists: {self.file_path}",
                file_path=str(self.file_path),
                original_exception=e,
            ) from e
        except OSError as e:
            raise FileDiscardError(
                message=f"Failed to discard file: {self.file_path}",
                file_path=str(self.file_path),
                original_exception=e,
            ) from e


class MockFileReader:
    """
    Mock implementation of FileReader for testing.

    Returns configurable file contents, allowing tests to control file reading
    behavior without requiring filesystem operations or actual file I/O.
    """

    def __init__(
        self,
        return_value: str | None = None,
        read_file_fn: Callable[[Path], str] | None = None,
    ):
        """
        Initialize MockFileReader with configurable reading behavior.

        Args:
            return_value: If provided, always returns this value regardless of input.
                Takes precedence over read_file_fn if both are provided.
            read_file_fn: Optional callable that takes a file path and returns file content.
                If return_value is None, this will be used. If both are None,
                defaults to returning empty string.

        Attributes (for test inspection):
            read_file_calls: List of file paths passed to read_file()
        """
        self.return_value = return_value
        self.read_file_fn = read_file_fn

        # Track calls for test inspection
        self.read_file_calls: list[Path] = []

    def read_file(self, file_path: Path) -> str:
        """
        Read the text content of a file (returns configured value, tracks call).

        Args:
            file_path: The path to the file to read.

        Returns:
            The configured return value or result of read_file_fn, or empty string by default.
        """
        self.read_file_calls.append(file_path)
        if self.return_value is not None:
            return self.return_value
        if self.read_file_fn is not None:
            return self.read_file_fn(file_path)
        return ""  # Default: return empty string


class MockFileWriter:
    """
    Mock implementation of FileWriter for testing.

    Tracks all method calls and optionally stores written data, allowing tests
    to verify writer interactions and inspect written content without filesystem operations.
    """

    def __init__(
        self,
        store_written_data: bool = False,
    ):
        """
        Initialize MockFileWriter with configurable behavior.

        Args:
            store_written_data: If True, stores all written data in attributes for inspection.
                Defaults to False for minimal memory usage.

        Attributes (for test inspection):
            write_file_calls: List of tuples (data, mode) passed to write_file()
            append_jsonl_line_calls: List of dictionaries passed to append_jsonl_line()
            append_processed_files_calls: List of tuples (results, mode) passed to append_processed_files()
            written_data: If store_written_data=True, accumulates all written string data
            written_jsonl_lines: If store_written_data=True, list of all appended JSONL dictionaries
        """
        self.store_written_data = store_written_data

        # Track calls for test inspection
        self.write_file_calls: list[tuple[str, str]] = []
        self.append_jsonl_line_calls: list[dict] = []
        self.append_processed_files_calls: list[
            tuple[dict[FileCategory, CategoryProcessedFiles], str]
        ] = []

        # Store written data if requested
        self.written_data: str = ""
        self.written_jsonl_lines: list[dict] = []

    def write_file(self, data: str, mode: str = "w") -> None:
        """
        Write data to a file (tracks call, optionally stores data).

        Args:
            data: String data to write.
            mode: File mode ("w" for write/truncate, "a" for append). Defaults to "w".
        """
        self.write_file_calls.append((data, mode))
        if self.store_written_data:
            if mode == "w":
                self.written_data = data
            else:  # mode == "a"
                self.written_data += data

    def append_jsonl_line(self, data: dict) -> None:
        """
        Append a JSON line to a file (tracks call, optionally stores data).

        Args:
            data: Dictionary to serialize as JSON and append.
        """
        self.append_jsonl_line_calls.append(data)
        if self.store_written_data:
            self.written_jsonl_lines.append(data)

    def append_processed_files(
        self, results: dict[FileCategory, CategoryProcessedFiles], mode: str = "a"
    ) -> None:
        """
        Append processed files to a file in JSONL format (tracks call, optionally stores data).

        Args:
            results: Dictionary mapping file categories to CategoryProcessedFiles.
            mode: File mode ("w" for write/truncate, "a" for append). Defaults to "a".
        """
        self.append_processed_files_calls.append((results, mode))
        if self.store_written_data:
            for _, status in results.items():
                for processed_file in status.files:
                    self.written_jsonl_lines.append(asdict(processed_file))
