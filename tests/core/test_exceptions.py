"""
Comprehensive tests for the exceptions module using pytest.

Tests cover:
- TempFileError: base exception for temporary file errors with diagnostic info
- TempFileCreationError: exception for temp file creation failures
- FileIOError: base exception for file I/O errors
- InvalidFilePathError: exception for invalid file paths
- FileWriteError: exception for file write failures
- FileReadError: exception for file read failures
- FileDiscardError: exception for file deletion failures
"""

import os
import pytest

from core.exceptions import (
    TempFileError,
    TempFileCreationError,
    FileIOError,
    InvalidFilePathError,
    FileWriteError,
    FileReadError,
    FileDiscardError,
)


# ============================================================================
# Tests for TempFileError
# ============================================================================


@pytest.mark.unit
def test_temp_file_error_default_message():
    """TempFileError should have a default message when none provided."""
    error = TempFileError()
    assert str(error) == "An error occurred with a temporary file"
    assert error.message == "An error occurred with a temporary file"
    assert error.original_exception is None


@pytest.mark.unit
def test_temp_file_error_custom_message():
    """TempFileError should accept and store a custom message."""
    custom_message = "Custom temp file error message"
    error = TempFileError(message=custom_message)
    assert str(error) == custom_message
    assert error.message == custom_message
    assert error.original_exception is None


@pytest.mark.unit
def test_temp_file_error_with_original_exception():
    """TempFileError should store the original exception and include it in diagnostic info."""
    original = ValueError("Original error occurred")
    error = TempFileError(original_exception=original)

    assert error.original_exception == original
    assert error.diagnostic_info["type"] == "ValueError"
    assert error.diagnostic_info["details"] == "Original error occurred"
    assert error.diagnostic_info["os_name"] == os.name


@pytest.mark.unit
def test_temp_file_error_with_message_and_exception():
    """TempFileError should store both custom message and original exception."""
    original = OSError("Permission denied")
    custom_message = "Failed to create temp file"
    error = TempFileError(message=custom_message, original_exception=original)

    assert str(error) == custom_message
    assert error.message == custom_message
    assert error.original_exception == original
    assert error.diagnostic_info["type"] == "OSError"
    assert error.diagnostic_info["details"] == "Permission denied"


@pytest.mark.unit
def test_temp_file_error_diagnostic_info_without_exception():
    """TempFileError diagnostic info should handle None original exception."""
    error = TempFileError()

    assert error.diagnostic_info["type"] == "Unknown"
    assert error.diagnostic_info["details"] == "No details"
    assert error.diagnostic_info["os_name"] == os.name


@pytest.mark.unit
@pytest.mark.parametrize(
    "exception_class,exception_message",
    [
        (ValueError, "Invalid value"),
        (OSError, "System error"),
        (PermissionError, "Access denied"),
        (FileNotFoundError, "File not found"),
    ],
)
def test_temp_file_error_various_exception_types(exception_class, exception_message):
    """TempFileError should correctly handle various exception types."""
    original = exception_class(exception_message)
    error = TempFileError(original_exception=original)

    assert error.diagnostic_info["type"] == exception_class.__name__
    assert error.diagnostic_info["details"] == exception_message


@pytest.mark.unit
def test_temp_file_error_inheritance():
    """TempFileError should inherit from Exception."""
    error = TempFileError()
    assert isinstance(error, Exception)


# ============================================================================
# Tests for TempFileCreationError
# ============================================================================


@pytest.mark.unit
def test_temp_file_creation_error_default():
    """TempFileCreationError should have default message when no args provided."""
    error = TempFileCreationError()
    assert str(error) == "Failed to create temporary file"
    assert error.message == "Failed to create temporary file"
    assert error.original_exception is None


@pytest.mark.unit
def test_temp_file_creation_error_with_original_exception():
    """TempFileCreationError should store original exception and include in diagnostic info."""
    original = OSError("Disk full")
    error = TempFileCreationError(original_exception=original)

    assert str(error) == "Failed to create temporary file"
    assert error.original_exception == original
    assert error.diagnostic_info["type"] == "OSError"
    assert error.diagnostic_info["details"] == "Disk full"


@pytest.mark.unit
def test_temp_file_creation_error_custom_message():
    """TempFileCreationError should use custom message when provided."""
    error = TempFileCreationError(message="Custom message")
    assert str(error) == "Custom message"
    assert error.message == "Custom message"


@pytest.mark.unit
def test_temp_file_creation_error_inheritance():
    """TempFileCreationError should inherit from TempFileError."""
    error = TempFileCreationError()
    assert isinstance(error, TempFileError)
    assert isinstance(error, Exception)


# ============================================================================
# Tests for FileIOError
# ============================================================================


@pytest.mark.unit
def test_file_io_error_default_message():
    """FileIOError should have a default message when none provided."""
    error = FileIOError()
    assert str(error) == "An error occurred during file I/O operation"
    assert error.message == "An error occurred during file I/O operation"
    assert error.file_path is None
    assert error.original_exception is None


@pytest.mark.unit
def test_file_io_error_custom_message():
    """FileIOError should accept and store a custom message."""
    custom_message = "Custom I/O error message"
    error = FileIOError(message=custom_message)
    assert str(error) == custom_message
    assert error.message == custom_message


@pytest.mark.unit
def test_file_io_error_with_file_path():
    """FileIOError should store the file path."""
    file_path = "/path/to/file.txt"
    error = FileIOError(file_path=file_path)
    assert error.file_path == file_path


@pytest.mark.unit
def test_file_io_error_with_original_exception():
    """FileIOError should store the original exception."""
    original = IOError("Read failed")
    error = FileIOError(original_exception=original)
    assert error.original_exception == original


@pytest.mark.unit
def test_file_io_error_with_all_parameters():
    """FileIOError should store message, file_path, and original_exception."""
    custom_message = "Failed to read file"
    file_path = "/path/to/data.txt"
    original = PermissionError("Access denied")

    error = FileIOError(
        message=custom_message,
        file_path=file_path,
        original_exception=original,
    )

    assert str(error) == custom_message
    assert error.message == custom_message
    assert error.file_path == file_path
    assert error.original_exception == original


@pytest.mark.unit
@pytest.mark.parametrize(
    "file_path",
    [
        "/absolute/path/file.txt",
        "relative/path/file.txt",
        "file.txt",
        "",
    ],
)
def test_file_io_error_various_paths(file_path):
    """FileIOError should accept various file path formats."""
    error = FileIOError(file_path=file_path)
    assert error.file_path == file_path


@pytest.mark.unit
def test_file_io_error_inheritance():
    """FileIOError should inherit from Exception."""
    error = FileIOError()
    assert isinstance(error, Exception)


# ============================================================================
# Tests for InvalidFilePathError
# ============================================================================


@pytest.mark.unit
def test_invalid_file_path_error_default():
    """InvalidFilePathError should have default message when no args provided."""
    error = InvalidFilePathError()
    assert str(error) == "Invalid file path provided"
    assert error.message == "Invalid file path provided"
    assert error.file_path is None
    assert error.original_exception is None


@pytest.mark.unit
def test_invalid_file_path_error_custom_message():
    """InvalidFilePathError should accept and use custom message."""
    custom_message = "Path does not exist"
    error = InvalidFilePathError(message=custom_message)
    assert str(error) == custom_message
    assert error.message == custom_message


@pytest.mark.unit
def test_invalid_file_path_error_with_file_path():
    """InvalidFilePathError should store the invalid file path."""
    file_path = "/nonexistent/path.txt"
    error = InvalidFilePathError(file_path=file_path)
    assert error.file_path == file_path


@pytest.mark.unit
def test_invalid_file_path_error_with_original_exception():
    """InvalidFilePathError should store the original exception."""
    original = FileNotFoundError("Parent directory missing")
    error = InvalidFilePathError(original_exception=original)
    assert error.original_exception == original


@pytest.mark.unit
def test_invalid_file_path_error_with_all_parameters():
    """InvalidFilePathError should store all parameters."""
    custom_message = "Path is not writable"
    file_path = "/readonly/path.txt"
    original = PermissionError("Write permission denied")

    error = InvalidFilePathError(
        message=custom_message,
        file_path=file_path,
        original_exception=original,
    )

    assert str(error) == custom_message
    assert error.message == custom_message
    assert error.file_path == file_path
    assert error.original_exception == original


@pytest.mark.unit
def test_invalid_file_path_error_inheritance():
    """InvalidFilePathError should inherit from FileIOError."""
    error = InvalidFilePathError()
    assert isinstance(error, FileIOError)
    assert isinstance(error, Exception)


# ============================================================================
# Tests for FileWriteError
# ============================================================================


@pytest.mark.unit
def test_file_write_error_default():
    """FileWriteError should have default message when no args provided."""
    error = FileWriteError()
    assert str(error) == "Failed to write to file"
    assert error.message == "Failed to write to file"
    assert error.file_path is None
    assert error.original_exception is None


@pytest.mark.unit
def test_file_write_error_custom_message():
    """FileWriteError should accept and use custom message."""
    custom_message = "Disk space exhausted"
    error = FileWriteError(message=custom_message)
    assert str(error) == custom_message
    assert error.message == custom_message


@pytest.mark.unit
def test_file_write_error_with_file_path():
    """FileWriteError should store the file path that failed to write."""
    file_path = "/path/to/output.txt"
    error = FileWriteError(file_path=file_path)
    assert error.file_path == file_path


@pytest.mark.unit
def test_file_write_error_with_original_exception():
    """FileWriteError should store the original exception."""
    original = OSError("No space left on device")
    error = FileWriteError(original_exception=original)
    assert error.original_exception == original


@pytest.mark.unit
def test_file_write_error_with_all_parameters():
    """FileWriteError should store all parameters."""
    custom_message = "Write operation failed"
    file_path = "/tmp/data.bin"
    original = IOError("I/O error during write")

    error = FileWriteError(
        message=custom_message,
        file_path=file_path,
        original_exception=original,
    )

    assert str(error) == custom_message
    assert error.message == custom_message
    assert error.file_path == file_path
    assert error.original_exception == original


@pytest.mark.unit
def test_file_write_error_inheritance():
    """FileWriteError should inherit from FileIOError."""
    error = FileWriteError()
    assert isinstance(error, FileIOError)
    assert isinstance(error, Exception)


# ============================================================================
# Tests for FileReadError
# ============================================================================


@pytest.mark.unit
def test_file_read_error_default():
    """FileReadError should have default message when no args provided."""
    error = FileReadError()
    assert str(error) == "Failed to read file"
    assert error.message == "Failed to read file"
    assert error.file_path is None
    assert error.original_exception is None


@pytest.mark.unit
def test_file_read_error_custom_message():
    """FileReadError should accept and use custom message."""
    custom_message = "File is locked"
    error = FileReadError(message=custom_message)
    assert str(error) == custom_message
    assert error.message == custom_message


@pytest.mark.unit
def test_file_read_error_with_file_path():
    """FileReadError should store the file path that failed to read."""
    file_path = "/path/to/input.txt"
    error = FileReadError(file_path=file_path)
    assert error.file_path == file_path


@pytest.mark.unit
def test_file_read_error_with_original_exception():
    """FileReadError should store the original exception."""
    original = PermissionError("Read permission denied")
    error = FileReadError(original_exception=original)
    assert error.original_exception == original


@pytest.mark.unit
def test_file_read_error_with_all_parameters():
    """FileReadError should store all parameters."""
    custom_message = "Cannot access file"
    file_path = "/protected/file.txt"
    original = FileNotFoundError("File does not exist")

    error = FileReadError(
        message=custom_message,
        file_path=file_path,
        original_exception=original,
    )

    assert str(error) == custom_message
    assert error.message == custom_message
    assert error.file_path == file_path
    assert error.original_exception == original


@pytest.mark.unit
def test_file_read_error_inheritance():
    """FileReadError should inherit from FileIOError."""
    error = FileReadError()
    assert isinstance(error, FileIOError)
    assert isinstance(error, Exception)


# ============================================================================
# Tests for FileDiscardError
# ============================================================================


@pytest.mark.unit
def test_file_discard_error_default():
    """FileDiscardError should have default message when no args provided."""
    error = FileDiscardError()
    assert str(error) == "Failed to discard file"
    assert error.message == "Failed to discard file"
    assert error.file_path is None
    assert error.original_exception is None


@pytest.mark.unit
def test_file_discard_error_custom_message():
    """FileDiscardError should accept and use custom message."""
    custom_message = "File is in use"
    error = FileDiscardError(message=custom_message)
    assert str(error) == custom_message
    assert error.message == custom_message


@pytest.mark.unit
def test_file_discard_error_with_file_path():
    """FileDiscardError should store the file path that failed to discard."""
    file_path = "/path/to/temp.txt"
    error = FileDiscardError(file_path=file_path)
    assert error.file_path == file_path


@pytest.mark.unit
def test_file_discard_error_with_original_exception():
    """FileDiscardError should store the original exception."""
    original = PermissionError("Delete permission denied")
    error = FileDiscardError(original_exception=original)
    assert error.original_exception == original


@pytest.mark.unit
def test_file_discard_error_with_all_parameters():
    """FileDiscardError should store all parameters."""
    custom_message = "Cannot delete file"
    file_path = "/locked/file.txt"
    original = OSError("File is locked")

    error = FileDiscardError(
        message=custom_message,
        file_path=file_path,
        original_exception=original,
    )

    assert str(error) == custom_message
    assert error.message == custom_message
    assert error.file_path == file_path
    assert error.original_exception == original


@pytest.mark.unit
def test_file_discard_error_inheritance():
    """FileDiscardError should inherit from FileIOError."""
    error = FileDiscardError()
    assert isinstance(error, FileIOError)
    assert isinstance(error, Exception)


# ============================================================================
# Tests for Exception Hierarchy and Relationships
# ============================================================================


@pytest.mark.unit
def test_exception_hierarchy_temp_file():
    """TempFileCreationError should be part of TempFileError hierarchy."""
    error = TempFileCreationError()
    assert isinstance(error, TempFileError)
    assert isinstance(error, Exception)
    assert not isinstance(error, FileIOError)


@pytest.mark.unit
def test_exception_hierarchy_file_io():
    """FileIOError subclasses should be part of FileIOError hierarchy."""
    invalid_path = InvalidFilePathError()
    write_error = FileWriteError()
    read_error = FileReadError()
    discard_error = FileDiscardError()

    for error in [invalid_path, write_error, read_error, discard_error]:
        assert isinstance(error, FileIOError)
        assert isinstance(error, Exception)
        assert not isinstance(error, TempFileError)


@pytest.mark.unit
def test_exception_hierarchy_separation():
    """TempFileError and FileIOError hierarchies should be separate."""
    temp_error = TempFileError()
    io_error = FileIOError()

    assert not isinstance(temp_error, FileIOError)
    assert not isinstance(io_error, TempFileError)
    assert isinstance(temp_error, Exception)
    assert isinstance(io_error, Exception)


# ============================================================================
# Tests for Edge Cases
# ============================================================================


@pytest.mark.unit
def test_temp_file_error_empty_string_message():
    """TempFileError should handle empty string message (treated as None)."""
    error = TempFileError(message="")
    # Empty string is falsy, so should use default
    assert error.message == "An error occurred with a temporary file"


@pytest.mark.unit
def test_file_io_error_empty_string_message():
    """FileIOError should handle empty string message (treated as None)."""
    error = FileIOError(message="")
    # Empty string is falsy, so should use default
    assert error.message == "An error occurred during file I/O operation"


@pytest.mark.unit
def test_file_io_error_empty_string_path():
    """FileIOError should accept empty string as file path."""
    error = FileIOError(file_path="")
    assert error.file_path == ""


@pytest.mark.unit
def test_exception_with_none_values():
    """Exceptions should handle None values for optional parameters."""
    error = FileIOError(
        message=None,
        file_path=None,
        original_exception=None,
    )
    assert error.message == "An error occurred during file I/O operation"
    assert error.file_path is None
    assert error.original_exception is None


@pytest.mark.unit
def test_exception_string_representation():
    """Exceptions should have proper string representation."""
    error1 = TempFileError(message="Test error")
    error2 = FileIOError(message="I/O error")

    assert str(error1) == "Test error"
    assert str(error2) == "I/O error"
    assert repr(error1)  # Should have some representation
    assert repr(error2)  # Should have some representation
