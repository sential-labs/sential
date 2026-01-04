"""
Custom exception classes for the Sential CLI.

This module defines application-specific exceptions that are raised during
file discovery, inventory generation, and payload creation operations.
These exceptions provide structured error information and diagnostic data
to help with debugging and error reporting.
"""

import os
from typing import Optional


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
        message: Optional[str] = None,
        original_exception: Optional[Exception] = None,
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
        message: Optional[str] = None,
        original_exception: Optional[Exception] = None,
    ):
        super().__init__(
            message="Failed to create temporary file",
            original_exception=original_exception,
        )


class TempFileWriteError(TempFileError):
    """
    Raised when data cannot be written to a temporary file.

    This exception is raised when a write operation to a temporary file fails,
    typically due to disk space, filesystem errors, or permission issues.
    """

    def __init__(
        self,
        message: Optional[str] = None,
        original_exception: Optional[Exception] = None,
    ):
        super().__init__(
            message="Failed to write to temporary file",
            original_exception=original_exception,
        )


class EmptyInventoryError(Exception):
    """
    Raised when no files are found matching the specified criteria.

    This exception is raised when the file discovery process completes but finds
    no files that match the specified language and scope filters. This typically
    indicates that either the repository doesn't contain files of the target language,
    or the selected scopes are too restrictive.

    Attributes:
        message: A human-readable error message explaining that no matching files were found.
    """

    def __init__(self, message: Optional[str] = None):
        self.message = (
            message or "No files found matching the specified language and scopes"
        )
        super().__init__(self.message)
