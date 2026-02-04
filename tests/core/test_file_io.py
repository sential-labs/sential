"""
Comprehensive tests for the file_io module using pytest.

Tests cover:
- FilesystemFileReader: reading files, handling binary files, I/O errors
- FilesystemFileWriter: factory methods, writing files, appending JSONL, discarding files
- MockFileReader: call tracking and configurable return values
- MockFileWriter: call tracking and data storage
"""

import json
import os
import tempfile
from pathlib import Path
import pytest

from core.file_io import (
    FilesystemFileReader,
    FilesystemFileWriter,
    MockFileReader,
    MockFileWriter,
)
from core.exceptions import (
    FileReadError,
    FileWriteError,
    FileDiscardError,
    InvalidFilePathError,
    TempFileCreationError,
)
from core.models import FileCategory, CategoryProcessedFiles, ProcessedFile


# ============================================================================
# Tests for FilesystemFileReader.read_file
# ============================================================================


@pytest.mark.unit
def test_read_file_success(tmp_path):
    """Should successfully read a text file."""
    file_path = tmp_path / "test.txt"
    content = "Hello, world!\nThis is a test file."
    file_path.write_text(content, encoding="utf-8")

    reader = FilesystemFileReader()
    result = reader.read_file(file_path)

    assert result == content


@pytest.mark.unit
def test_read_file_nonexistent(tmp_path):
    """Should return empty string for non-existent file."""
    file_path = tmp_path / "nonexistent.txt"

    reader = FilesystemFileReader()
    result = reader.read_file(file_path)

    assert result == ""


@pytest.mark.unit
def test_read_file_binary_with_null_bytes(tmp_path):
    """Should return empty string for binary file with null bytes."""
    file_path = tmp_path / "binary.bin"
    # Write binary data with null bytes
    file_path.write_bytes(b"\x00\x01\x02\x03Hello\x00World")

    reader = FilesystemFileReader()
    result = reader.read_file(file_path)

    assert result == ""


@pytest.mark.unit
def test_read_file_invalid_utf8_ignored(tmp_path):
    """Should read file with invalid UTF-8, ignoring invalid bytes."""
    file_path = tmp_path / "invalid.txt"
    # Write bytes that are not valid UTF-8 (but no null bytes)
    file_path.write_bytes(b"\xff\xfe\xfd")

    reader = FilesystemFileReader()
    result = reader.read_file(file_path)

    # Invalid UTF-8 bytes are ignored, so result is empty string
    assert result == ""


@pytest.mark.unit
def test_read_file_mixed_valid_invalid_utf8(tmp_path):
    """Should read file with mixed valid and invalid UTF-8, ignoring invalid bytes."""
    file_path = tmp_path / "mixed.txt"
    # Write valid text followed by invalid UTF-8 bytes
    file_path.write_text("Valid text", encoding="utf-8")
    # Append invalid bytes (no null bytes)
    with file_path.open("ab") as f:
        f.write(b"\xff\xfe")

    reader = FilesystemFileReader()
    result = reader.read_file(file_path)

    # Should return the valid part, ignoring invalid bytes
    assert result == "Valid text"


@pytest.mark.unit
def test_read_file_io_error(tmp_path, mocker):
    """Should raise FileReadError when I/O error occurs."""
    file_path = tmp_path / "test.txt"
    file_path.write_text("content", encoding="utf-8")

    reader = FilesystemFileReader()

    # Mock open to raise OSError
    mock_open = mocker.patch("pathlib.Path.open")
    mock_open.side_effect = OSError("Permission denied")

    with pytest.raises(FileReadError) as exc_info:
        reader.read_file(file_path)

    assert "Failed to read file" in str(exc_info.value)
    assert str(file_path) in str(exc_info.value)
    assert exc_info.value.original_exception is not None


@pytest.mark.unit
def test_read_file_empty_file(tmp_path):
    """Should return empty string for empty file."""
    file_path = tmp_path / "empty.txt"
    file_path.touch()

    reader = FilesystemFileReader()
    result = reader.read_file(file_path)

    assert result == ""


@pytest.mark.unit
def test_read_file_multiline_content(tmp_path):
    """Should read multiline content correctly."""
    file_path = tmp_path / "multiline.txt"
    content = "Line 1\nLine 2\nLine 3\n"
    file_path.write_text(content, encoding="utf-8")

    reader = FilesystemFileReader()
    result = reader.read_file(file_path)

    assert result == content
    assert result.count("\n") == 3


# ============================================================================
# Tests for FilesystemFileReader._is_binary_file
# ============================================================================


@pytest.mark.unit
def test_is_binary_file_text_file(tmp_path):
    """Should return False for text file."""
    file_path = tmp_path / "text.txt"
    file_path.write_text("This is plain text", encoding="utf-8")

    reader = FilesystemFileReader()
    result = reader._is_binary_file(file_path)

    assert result is False


@pytest.mark.unit
def test_is_binary_file_with_null_bytes(tmp_path):
    """Should return True for file with null bytes."""
    file_path = tmp_path / "binary.bin"
    file_path.write_bytes(b"Text\x00with\x00nulls")

    reader = FilesystemFileReader()
    result = reader._is_binary_file(file_path)

    assert result is True


@pytest.mark.unit
def test_is_binary_file_invalid_utf8_no_null_bytes(tmp_path):
    """Should return False for file with invalid UTF-8 but no null bytes."""
    file_path = tmp_path / "invalid.txt"
    file_path.write_bytes(b"\xff\xfe\xfd")

    reader = FilesystemFileReader()
    result = reader._is_binary_file(file_path)

    # Invalid UTF-8 alone doesn't make a file binary - only null bytes do
    assert result is False


@pytest.mark.unit
def test_is_binary_file_unreadable(tmp_path, mocker):
    """Should return True when file cannot be read."""
    file_path = tmp_path / "unreadable.bin"

    reader = FilesystemFileReader()

    # Mock open to raise OSError
    mock_open = mocker.patch("builtins.open")
    mock_open.side_effect = OSError("Permission denied")

    result = reader._is_binary_file(file_path)

    assert result is True


@pytest.mark.unit
def test_is_binary_file_large_text_file(tmp_path):
    """Should return False for large text file without null bytes."""
    file_path = tmp_path / "large.txt"
    # Create a file larger than 1024 bytes
    content = "A" * 2000
    file_path.write_text(content, encoding="utf-8")

    reader = FilesystemFileReader()
    result = reader._is_binary_file(file_path)

    assert result is False


# ============================================================================
# Tests for FilesystemFileWriter.from_path
# ============================================================================


@pytest.mark.unit
def test_from_path_success(tmp_path):
    """Should create writer with valid path."""
    file_path = tmp_path / "output.jsonl"

    writer = FilesystemFileWriter.from_path(file_path)

    assert writer.file_path == file_path
    assert isinstance(writer, FilesystemFileWriter)


@pytest.mark.unit
def test_from_path_parent_not_exists(tmp_path):
    """Should raise InvalidFilePathError when parent directory doesn't exist."""
    file_path = tmp_path / "nonexistent" / "output.jsonl"

    with pytest.raises(InvalidFilePathError) as exc_info:
        FilesystemFileWriter.from_path(file_path)

    assert "Parent directory does not exist" in str(exc_info.value)
    assert exc_info.value.file_path == str(file_path)


@pytest.mark.unit
def test_from_path_parent_not_writable(tmp_path):
    """Should raise InvalidFilePathError when parent directory is not writable."""
    if os.name == "nt":  # Windows doesn't support chmod the same way
        pytest.skip("Skipping on Windows - chmod behavior differs")

    file_path = tmp_path / "output.jsonl"
    # Make parent directory read-only
    tmp_path.chmod(0o444)

    try:
        with pytest.raises(InvalidFilePathError) as exc_info:
            FilesystemFileWriter.from_path(file_path)

        assert "Parent directory is not writable" in str(exc_info.value)
        assert exc_info.value.file_path == str(file_path)
    finally:
        # Restore permissions for cleanup
        tmp_path.chmod(0o755)


# ============================================================================
# Tests for FilesystemFileWriter.from_tempfile
# ============================================================================


@pytest.mark.unit
def test_from_tempfile_success():
    """Should create writer with tempfile."""
    writer = FilesystemFileWriter.from_tempfile(suffix=".jsonl")

    assert writer.file_path is not None
    assert writer.file_path.suffix == ".jsonl"
    assert writer.file_path.exists() is True  # File created but closed
    assert isinstance(writer, FilesystemFileWriter)


@pytest.mark.unit
def test_from_tempfile_custom_suffix():
    """Should create tempfile with custom suffix."""
    writer = FilesystemFileWriter.from_tempfile(suffix=".txt")

    assert writer.file_path.suffix == ".txt"


@pytest.mark.unit
def test_from_tempfile_creation_error(mocker):
    """Should raise TempFileCreationError when tempfile creation fails."""
    mock_mkstemp = mocker.patch("tempfile.mkstemp")
    mock_mkstemp.side_effect = OSError("Disk full")

    with pytest.raises(TempFileCreationError) as exc_info:
        FilesystemFileWriter.from_tempfile()

    assert exc_info.value.original_exception is not None


# ============================================================================
# Tests for FilesystemFileWriter.from_named_tempfile
# ============================================================================


@pytest.mark.unit
def test_from_named_tempfile_success():
    """Should create writer with named tempfile."""
    writer = FilesystemFileWriter.from_named_tempfile(name="test", suffix=".jsonl")

    assert writer.file_path is not None
    assert writer.file_path.name == "test.jsonl"
    assert writer.file_path.parent == Path(tempfile.gettempdir())
    assert isinstance(writer, FilesystemFileWriter)


@pytest.mark.unit
def test_from_named_tempfile_custom_suffix():
    """Should create named tempfile with custom suffix."""
    writer = FilesystemFileWriter.from_named_tempfile(name="output", suffix=".txt")

    assert writer.file_path.name == "output.txt"


@pytest.mark.unit
def test_from_named_tempfile_temp_dir_not_writable(mocker):
    """Should raise TempFileCreationError when temp directory is not writable."""
    mock_gettempdir = mocker.patch("tempfile.gettempdir")
    mock_gettempdir.return_value = "/nonexistent/dir"

    mock_access = mocker.patch("os.access")
    mock_access.return_value = False

    with pytest.raises(TempFileCreationError) as exc_info:
        FilesystemFileWriter.from_named_tempfile(name="test")

    assert "Temp directory is not writable" in str(exc_info.value)


@pytest.mark.unit
def test_from_named_tempfile_os_error(mocker):
    """Should raise TempFileCreationError on OSError."""
    mock_gettempdir = mocker.patch("tempfile.gettempdir")
    mock_gettempdir.side_effect = OSError("Temp dir access failed")

    with pytest.raises(TempFileCreationError) as exc_info:
        FilesystemFileWriter.from_named_tempfile(name="test")

    assert "Failed to create named tempfile" in str(exc_info.value)
    assert exc_info.value.original_exception is not None


# ============================================================================
# Tests for FilesystemFileWriter.write_file
# ============================================================================


@pytest.mark.unit
def test_write_file_success(tmp_path):
    """Should write data to file successfully."""
    file_path = tmp_path / "output.txt"
    writer = FilesystemFileWriter.from_path(file_path)
    data = "Hello, world!"

    writer.write_file(data)

    assert file_path.read_text(encoding="utf-8") == data


@pytest.mark.unit
def test_write_file_write_mode(tmp_path):
    """Should truncate file in write mode."""
    file_path = tmp_path / "output.txt"
    writer = FilesystemFileWriter.from_path(file_path)
    writer.write_file("First content")

    writer.write_file("Second content", mode="w")

    assert file_path.read_text(encoding="utf-8") == "Second content"


@pytest.mark.unit
def test_write_file_append_mode(tmp_path):
    """Should append data in append mode."""
    file_path = tmp_path / "output.txt"
    writer = FilesystemFileWriter.from_path(file_path)
    writer.write_file("First line\n")

    writer.write_file("Second line\n", mode="a")

    content = file_path.read_text(encoding="utf-8")
    assert content == "First line\nSecond line\n"


@pytest.mark.unit
def test_write_file_no_file_path():
    """Should raise InvalidFilePathError when file path is not set."""
    writer = FilesystemFileWriter()  # No file_path set

    with pytest.raises(InvalidFilePathError) as exc_info:
        writer.write_file("data")

    assert "No file path set" in str(exc_info.value)


@pytest.mark.unit
def test_write_file_io_error(tmp_path, mocker):
    """Should raise FileWriteError when write fails."""
    file_path = tmp_path / "output.txt"
    writer = FilesystemFileWriter.from_path(file_path)

    # Mock open to raise OSError
    mock_open = mocker.patch("builtins.open")
    mock_open.side_effect = OSError("Disk full")

    with pytest.raises(FileWriteError) as exc_info:
        writer.write_file("data")

    assert "Failed to write to file" in str(exc_info.value)
    assert str(file_path) in str(exc_info.value)
    assert exc_info.value.original_exception is not None


@pytest.mark.unit
def test_write_file_multiline_content(tmp_path):
    """Should write multiline content correctly."""
    file_path = tmp_path / "output.txt"
    writer = FilesystemFileWriter.from_path(file_path)
    data = "Line 1\nLine 2\nLine 3\n"

    writer.write_file(data)

    assert file_path.read_text(encoding="utf-8") == data


# ============================================================================
# Tests for FilesystemFileWriter.append_jsonl_line
# ============================================================================


@pytest.mark.unit
def test_append_jsonl_line_success(tmp_path):
    """Should append JSON line to file successfully."""
    file_path = tmp_path / "output.jsonl"
    writer = FilesystemFileWriter.from_path(file_path)
    data = {"key": "value", "number": 42}

    writer.append_jsonl_line(data)

    lines = file_path.read_text(encoding="utf-8").strip().split("\n")
    assert len(lines) == 1
    assert json.loads(lines[0]) == data


@pytest.mark.unit
def test_append_jsonl_line_multiple_lines(tmp_path):
    """Should append multiple JSON lines correctly."""
    file_path = tmp_path / "output.jsonl"
    writer = FilesystemFileWriter.from_path(file_path)

    writer.append_jsonl_line({"id": 1})
    writer.append_jsonl_line({"id": 2})
    writer.append_jsonl_line({"id": 3})

    lines = file_path.read_text(encoding="utf-8").strip().split("\n")
    assert len(lines) == 3
    assert json.loads(lines[0]) == {"id": 1}
    assert json.loads(lines[1]) == {"id": 2}
    assert json.loads(lines[2]) == {"id": 3}


@pytest.mark.unit
def test_append_jsonl_line_no_file_path():
    """Should raise InvalidFilePathError when file path is not set."""
    writer = FilesystemFileWriter()

    with pytest.raises(InvalidFilePathError) as exc_info:
        writer.append_jsonl_line({"key": "value"})

    assert "No file path set" in str(exc_info.value)


@pytest.mark.unit
def test_append_jsonl_line_io_error(tmp_path, mocker):
    """Should raise FileWriteError when append fails."""
    file_path = tmp_path / "output.jsonl"
    writer = FilesystemFileWriter.from_path(file_path)

    mock_open = mocker.patch("builtins.open")
    mock_open.side_effect = OSError("Disk full")

    with pytest.raises(FileWriteError) as exc_info:
        writer.append_jsonl_line({"key": "value"})

    assert "Failed to append JSON line to file" in str(exc_info.value)
    assert str(file_path) in str(exc_info.value)


@pytest.mark.unit
def test_append_jsonl_line_complex_data(tmp_path):
    """Should handle complex nested dictionaries."""
    file_path = tmp_path / "output.jsonl"
    writer = FilesystemFileWriter.from_path(file_path)
    data = {
        "nested": {"key": "value"},
        "list": [1, 2, 3],
        "string": "text",
        "number": 42,
        "boolean": True,
    }

    writer.append_jsonl_line(data)

    lines = file_path.read_text(encoding="utf-8").strip().split("\n")
    assert json.loads(lines[0]) == data


# ============================================================================
# Tests for FilesystemFileWriter.append_processed_files
# ============================================================================


@pytest.mark.unit
def test_append_processed_files_success(tmp_path):
    """Should append processed files to file successfully."""
    file_path = tmp_path / "output.jsonl"
    writer = FilesystemFileWriter.from_path(file_path)

    results = {
        FileCategory.SOURCE: CategoryProcessedFiles(FileCategory.SOURCE),
        FileCategory.MANIFEST: CategoryProcessedFiles(FileCategory.MANIFEST),
    }
    results[FileCategory.SOURCE].append(
        ProcessedFile("file1.py", FileCategory.SOURCE.value, "content1")
    )
    results[FileCategory.SOURCE].append(
        ProcessedFile("file2.py", FileCategory.SOURCE.value, "content2")
    )
    results[FileCategory.MANIFEST].append(
        ProcessedFile("package.json", FileCategory.MANIFEST.value, "{}")
    )

    writer.append_processed_files(results)

    lines = file_path.read_text(encoding="utf-8").strip().split("\n")
    assert len(lines) == 3
    assert json.loads(lines[0])["path"] == "file1.py"
    assert json.loads(lines[1])["path"] == "file2.py"
    assert json.loads(lines[2])["path"] == "package.json"


@pytest.mark.unit
def test_append_processed_files_write_mode(tmp_path):
    """Should truncate file in write mode."""
    file_path = tmp_path / "output.jsonl"
    writer = FilesystemFileWriter.from_path(file_path)

    # Write initial data
    results1 = {
        FileCategory.SOURCE: CategoryProcessedFiles(FileCategory.SOURCE),
    }
    results1[FileCategory.SOURCE].append(
        ProcessedFile("old.py", FileCategory.SOURCE.value, "old")
    )
    writer.append_processed_files(results1, mode="w")

    # Write new data in write mode
    results2 = {
        FileCategory.SOURCE: CategoryProcessedFiles(FileCategory.SOURCE),
    }
    results2[FileCategory.SOURCE].append(
        ProcessedFile("new.py", FileCategory.SOURCE.value, "new")
    )
    writer.append_processed_files(results2, mode="w")

    lines = file_path.read_text(encoding="utf-8").strip().split("\n")
    assert len(lines) == 1
    assert json.loads(lines[0])["path"] == "new.py"


@pytest.mark.unit
def test_append_processed_files_append_mode(tmp_path):
    """Should append data in append mode."""
    file_path = tmp_path / "output.jsonl"
    writer = FilesystemFileWriter.from_path(file_path)

    results1 = {
        FileCategory.SOURCE: CategoryProcessedFiles(FileCategory.SOURCE),
    }
    results1[FileCategory.SOURCE].append(
        ProcessedFile("file1.py", FileCategory.SOURCE.value, "content1")
    )
    writer.append_processed_files(results1, mode="a")

    results2 = {
        FileCategory.SOURCE: CategoryProcessedFiles(FileCategory.SOURCE),
    }
    results2[FileCategory.SOURCE].append(
        ProcessedFile("file2.py", FileCategory.SOURCE.value, "content2")
    )
    writer.append_processed_files(results2, mode="a")

    lines = file_path.read_text(encoding="utf-8").strip().split("\n")
    assert len(lines) == 2


@pytest.mark.unit
def test_append_processed_files_empty_results(tmp_path):
    """Should handle empty results dictionary."""
    file_path = tmp_path / "output.jsonl"
    writer = FilesystemFileWriter.from_path(file_path)

    writer.append_processed_files({})

    content = file_path.read_text(encoding="utf-8")
    assert content == ""


@pytest.mark.unit
def test_append_processed_files_no_file_path():
    """Should raise InvalidFilePathError when file path is not set."""
    writer = FilesystemFileWriter()
    results = {FileCategory.SOURCE: CategoryProcessedFiles(FileCategory.SOURCE)}

    with pytest.raises(InvalidFilePathError) as exc_info:
        writer.append_processed_files(results)

    assert "No file path set" in str(exc_info.value)


@pytest.mark.unit
def test_append_processed_files_io_error(tmp_path, mocker):
    """Should raise FileWriteError when write fails."""
    file_path = tmp_path / "output.jsonl"
    writer = FilesystemFileWriter.from_path(file_path)
    results = {FileCategory.SOURCE: CategoryProcessedFiles(FileCategory.SOURCE)}

    mock_open = mocker.patch("builtins.open")
    mock_open.side_effect = OSError("Disk full")

    with pytest.raises(FileWriteError) as exc_info:
        writer.append_processed_files(results)

    assert "Failed to append processed files to file" in str(exc_info.value)
    assert str(file_path) in str(exc_info.value)


# ============================================================================
# Tests for FilesystemFileWriter.discard
# ============================================================================


@pytest.mark.unit
def test_discard_success(tmp_path):
    """Should delete file successfully."""
    file_path = tmp_path / "output.jsonl"
    file_path.write_text("content", encoding="utf-8")
    writer = FilesystemFileWriter.from_path(file_path)

    writer.discard()

    assert file_path.exists() is False


@pytest.mark.unit
def test_discard_no_file_path():
    """Should raise InvalidFilePathError when file path is not set."""
    writer = FilesystemFileWriter()

    with pytest.raises(InvalidFilePathError) as exc_info:
        writer.discard()

    assert "No file path set" in str(exc_info.value)


@pytest.mark.unit
def test_discard_file_not_found(tmp_path):
    """Should raise FileDiscardError when file doesn't exist."""
    file_path = tmp_path / "nonexistent.jsonl"
    writer = FilesystemFileWriter.from_path(file_path)

    with pytest.raises(FileDiscardError) as exc_info:
        writer.discard()

    assert "Cannot discard file since it no longer exists" in str(exc_info.value)
    assert str(file_path) in str(exc_info.value)
    assert exc_info.value.original_exception is not None


@pytest.mark.unit
def test_discard_os_error(tmp_path, mocker):
    """Should raise FileDiscardError on OSError."""
    file_path = tmp_path / "output.jsonl"
    file_path.write_text("content", encoding="utf-8")
    writer = FilesystemFileWriter.from_path(file_path)

    mock_unlink = mocker.patch("pathlib.Path.unlink")
    mock_unlink.side_effect = OSError("Permission denied")

    with pytest.raises(FileDiscardError) as exc_info:
        writer.discard()

    assert "Failed to discard file" in str(exc_info.value)
    assert str(file_path) in str(exc_info.value)
    assert exc_info.value.original_exception is not None


# ============================================================================
# Tests for MockFileReader
# ============================================================================


@pytest.mark.unit
def test_mock_file_reader_return_value():
    """Should return configured return_value."""
    reader = MockFileReader(return_value="fixed content")

    result = reader.read_file(Path("any/path.txt"))

    assert result == "fixed content"
    assert len(reader.read_file_calls) == 1
    assert reader.read_file_calls[0] == Path("any/path.txt")


@pytest.mark.unit
def test_mock_file_reader_read_file_fn():
    """Should use read_file_fn when return_value is None."""

    def custom_read(path: Path) -> str:
        return f"Content from {path.name}"

    reader = MockFileReader(read_file_fn=custom_read)

    result = reader.read_file(Path("test.txt"))

    assert result == "Content from test.txt"
    assert len(reader.read_file_calls) == 1


@pytest.mark.unit
def test_mock_file_reader_default_empty():
    """Should return empty string by default."""
    reader = MockFileReader()

    result = reader.read_file(Path("test.txt"))

    assert result == ""
    assert len(reader.read_file_calls) == 1


@pytest.mark.unit
def test_mock_file_reader_return_value_takes_precedence():
    """Should use return_value even when read_file_fn is provided."""

    def custom_read(path: Path) -> str:
        return f"Content from {path.name}"

    reader = MockFileReader(return_value="fixed", read_file_fn=custom_read)

    result = reader.read_file(Path("test.txt"))

    assert result == "fixed"  # return_value takes precedence


@pytest.mark.unit
def test_mock_file_reader_tracks_multiple_calls():
    """Should track all read_file calls."""
    reader = MockFileReader(return_value="content")

    reader.read_file(Path("file1.txt"))
    reader.read_file(Path("file2.txt"))
    reader.read_file(Path("file3.txt"))

    assert len(reader.read_file_calls) == 3
    assert reader.read_file_calls[0] == Path("file1.txt")
    assert reader.read_file_calls[1] == Path("file2.txt")
    assert reader.read_file_calls[2] == Path("file3.txt")


# ============================================================================
# Tests for MockFileWriter
# ============================================================================


@pytest.mark.unit
def test_mock_file_writer_write_file_tracks_calls():
    """Should track write_file calls."""
    writer = MockFileWriter()

    writer.write_file("data1", mode="w")
    writer.write_file("data2", mode="a")

    assert len(writer.write_file_calls) == 2
    assert writer.write_file_calls[0] == ("data1", "w")
    assert writer.write_file_calls[1] == ("data2", "a")


@pytest.mark.unit
def test_mock_file_writer_write_file_stores_data_write_mode():
    """Should store data in write mode when store_written_data=True."""
    writer = MockFileWriter(store_written_data=True)

    writer.write_file("first", mode="w")
    writer.write_file("second", mode="w")

    assert writer.written_data == "second"  # Write mode truncates


@pytest.mark.unit
def test_mock_file_writer_write_file_stores_data_append_mode():
    """Should append data in append mode when store_written_data=True."""
    writer = MockFileWriter(store_written_data=True)

    writer.write_file("first", mode="a")
    writer.write_file("second", mode="a")

    assert writer.written_data == "firstsecond"


@pytest.mark.unit
def test_mock_file_writer_write_file_no_storage():
    """Should not store data when store_written_data=False."""
    writer = MockFileWriter(store_written_data=False)

    writer.write_file("data", mode="w")

    assert writer.written_data == ""


@pytest.mark.unit
def test_mock_file_writer_append_jsonl_line_tracks_calls():
    """Should track append_jsonl_line calls."""
    writer = MockFileWriter()

    writer.append_jsonl_line({"key1": "value1"})
    writer.append_jsonl_line({"key2": "value2"})

    assert len(writer.append_jsonl_line_calls) == 2
    assert writer.append_jsonl_line_calls[0] == {"key1": "value1"}
    assert writer.append_jsonl_line_calls[1] == {"key2": "value2"}


@pytest.mark.unit
def test_mock_file_writer_append_jsonl_line_stores_data():
    """Should store JSONL data when store_written_data=True."""
    writer = MockFileWriter(store_written_data=True)

    writer.append_jsonl_line({"id": 1})
    writer.append_jsonl_line({"id": 2})

    assert len(writer.written_jsonl_lines) == 2
    assert writer.written_jsonl_lines[0] == {"id": 1}
    assert writer.written_jsonl_lines[1] == {"id": 2}


@pytest.mark.unit
def test_mock_file_writer_append_jsonl_line_no_storage():
    """Should not store JSONL data when store_written_data=False."""
    writer = MockFileWriter(store_written_data=False)

    writer.append_jsonl_line({"key": "value"})

    assert len(writer.written_jsonl_lines) == 0


@pytest.mark.unit
def test_mock_file_writer_append_processed_files_tracks_calls():
    """Should track append_processed_files calls."""
    writer = MockFileWriter()
    results = {
        FileCategory.SOURCE: CategoryProcessedFiles(FileCategory.SOURCE),
    }
    results[FileCategory.SOURCE].append(
        ProcessedFile("file.py", FileCategory.SOURCE.value, "content")
    )

    writer.append_processed_files(results, mode="a")

    assert len(writer.append_processed_files_calls) == 1
    assert writer.append_processed_files_calls[0][1] == "a"
    assert FileCategory.SOURCE in writer.append_processed_files_calls[0][0]


@pytest.mark.unit
def test_mock_file_writer_append_processed_files_stores_data():
    """Should store processed files data when store_written_data=True."""
    writer = MockFileWriter(store_written_data=True)
    results = {
        FileCategory.SOURCE: CategoryProcessedFiles(FileCategory.SOURCE),
        FileCategory.MANIFEST: CategoryProcessedFiles(FileCategory.MANIFEST),
    }
    results[FileCategory.SOURCE].append(
        ProcessedFile("file1.py", FileCategory.SOURCE.value, "content1")
    )
    results[FileCategory.SOURCE].append(
        ProcessedFile("file2.py", FileCategory.SOURCE.value, "content2")
    )
    results[FileCategory.MANIFEST].append(
        ProcessedFile("package.json", FileCategory.MANIFEST.value, "{}")
    )

    writer.append_processed_files(results)

    assert len(writer.written_jsonl_lines) == 3
    assert writer.written_jsonl_lines[0]["path"] == "file1.py"
    assert writer.written_jsonl_lines[1]["path"] == "file2.py"
    assert writer.written_jsonl_lines[2]["path"] == "package.json"


@pytest.mark.unit
def test_mock_file_writer_append_processed_files_no_storage():
    """Should not store processed files data when store_written_data=False."""
    writer = MockFileWriter(store_written_data=False)
    results = {
        FileCategory.SOURCE: CategoryProcessedFiles(FileCategory.SOURCE),
    }
    results[FileCategory.SOURCE].append(
        ProcessedFile("file.py", FileCategory.SOURCE.value, "content")
    )

    writer.append_processed_files(results)

    assert len(writer.written_jsonl_lines) == 0


@pytest.mark.unit
def test_mock_file_writer_multiple_operations():
    """Should track all operations independently."""
    writer = MockFileWriter(store_written_data=True)

    writer.write_file("text", mode="w")
    writer.append_jsonl_line({"key": "value"})
    results = {FileCategory.SOURCE: CategoryProcessedFiles(FileCategory.SOURCE)}
    results[FileCategory.SOURCE].append(
        ProcessedFile("file.py", FileCategory.SOURCE.value, "content")
    )
    writer.append_processed_files(results)

    assert len(writer.write_file_calls) == 1
    assert len(writer.append_jsonl_line_calls) == 1
    assert len(writer.append_processed_files_calls) == 1
    assert writer.written_data == "text"
    assert (
        len(writer.written_jsonl_lines) == 2
    )  # One from append_jsonl_line, one from append_processed_files
