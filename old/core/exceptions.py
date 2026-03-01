"""
Custom exception classes for the Sential CLI.

This module defines application-specific exceptions that are raised during
file discovery, inventory generation, and payload creation operations.
These exceptions provide structured error information and diagnostic data
to help with debugging and error reporting.
"""

import os


class TempFileError(Exception):
    """
    Base exception for temporary file operation errors.

    This exception is raised when an error occurs while creating, writing to,
    or managing temporary files used during the inventory and extraction process.
    It includes diagnostic information about the operating system and the original
    exception that caused the error.

    Attributes:
        message: A human-readable error message describing what went wrong.
        original_exception: The underlying exception that caused this error, if any.
        diagnostic_info: A dictionary containing diagnostic information including
            exception type, details, and OS name.
    """

    def __init__(
        self,
        message: str | None = None,
        original_exception: Exception | None = None,
    ):
        self.message = message or "An error occurred with a temporary file"
        super().__init__(self.message)
        self.original_exception = original_exception
        self.diagnostic_info = {
            "type": (
                type(original_exception).__name__ if original_exception else "Unknown"
            ),
            "details": str(original_exception) if original_exception else "No details",
            "os_name": os.name,
        }


class TempFileCreationError(TempFileError):
    """
    Raised when a temporary file cannot be created.

    This exception is raised when the system fails to create a temporary file,
    typically due to filesystem permissions, disk space, or other system-level issues.
    """

    def __init__(
        self,
        message: str | None = None,
        original_exception: Exception | None = None,
    ):
        super().__init__(
            message=message or "Failed to create temporary file",
            original_exception=original_exception,
        )


class FileIOError(Exception):
    """
    Base exception for file I/O operation errors.

    This exception is raised when an error occurs during file reading or writing
    operations. It includes diagnostic information about the file path and the
    original exception that caused the error.

    Attributes:
        message: A human-readable error message describing what went wrong.
        file_path: The path to the file that caused the error, if available.
        original_exception: The underlying exception that caused this error, if any.
    """

    def __init__(
        self,
        message: str | None = None,
        file_path: str | None = None,
        original_exception: Exception | None = None,
    ):
        self.message = message or "An error occurred during file I/O operation"
        super().__init__(self.message)
        self.file_path = file_path
        self.original_exception = original_exception


class InvalidFilePathError(FileIOError):
    """
    Raised when a file path is invalid or cannot be used.

    This exception is raised when a file path is provided but cannot be used
    for the intended operation, such as when the parent directory doesn't exist,
    the path is not writable, or the path is not set when required.

    Attributes:
        message: A human-readable error message describing the path issue.
        file_path: The invalid file path.
        original_exception: The underlying exception that caused this error, if any.
    """

    def __init__(
        self,
        message: str | None = None,
        file_path: str | None = None,
        original_exception: Exception | None = None,
    ):
        super().__init__(
            message=message or "Invalid file path provided",
            file_path=file_path,
            original_exception=original_exception,
        )


class FileWriteError(FileIOError):
    """
    Raised when data cannot be written to a file.

    This exception is raised when a write operation to a file fails, typically
    due to disk space, filesystem errors, permission issues, or the file path
    not being set.

    Attributes:
        message: A human-readable error message describing the write failure.
        file_path: The path to the file that failed to write.
        original_exception: The underlying exception that caused this error, if any.
    """

    def __init__(
        self,
        message: str | None = None,
        file_path: str | None = None,
        original_exception: Exception | None = None,
    ):
        super().__init__(
            message=message or "Failed to write to file",
            file_path=file_path,
            original_exception=original_exception,
        )


class FileReadError(FileIOError):
    """
    Raised when a file cannot be read.

    This exception is raised when a read operation fails, typically due to
    permission issues, filesystem errors, or the file being inaccessible.

    Attributes:
        message: A human-readable error message describing the read failure.
        file_path: The path to the file that failed to read.
        original_exception: The underlying exception that caused this error, if any.
    """

    def __init__(
        self,
        message: str | None = None,
        file_path: str | None = None,
        original_exception: Exception | None = None,
    ):
        super().__init__(
            message=message or "Failed to read file",
            file_path=file_path,
            original_exception=original_exception,
        )


class FileDiscardError(FileIOError):
    """
    Raised when a file cannot be discarded (deleted).

    This exception is raised when attempting to delete a file fails, typically
    because the file doesn't exist, is locked, or permission is denied.

    Attributes:
        message: A human-readable error message describing the discard failure.
        file_path: The path to the file that failed to discard.
        original_exception: The underlying exception that caused this error, if any.
    """

    def __init__(
        self,
        message: str | None = None,
        file_path: str | None = None,
        original_exception: Exception | None = None,
    ):
        super().__init__(
            message=message or "Failed to discard file",
            file_path=file_path,
            original_exception=original_exception,
        )
