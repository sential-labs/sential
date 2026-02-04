"""
Comprehensive tests for the ctags adapter module using pytest.

Tests cover:
- _get_base_path: PyInstaller vs normal execution path resolution
- _normalize_system: platform system name normalization
- _normalize_architecture: machine architecture normalization
- _build_binary_pattern: binary filename pattern generation
- get_ctags_path: ctags binary location and selection
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from adapters.ctags import (
    _build_binary_pattern,
    _get_base_path,
    _normalize_architecture,
    _normalize_system,
    get_ctags_path,
)


# ============================================================================
# Tests for _get_base_path
# ============================================================================


@pytest.mark.unit
@pytest.mark.mock
def test_get_base_path_normal_execution(mocker):
    """_get_base_path should return parent.parent when not frozen."""
    # Mock sys to not have frozen attribute
    mock_sys = mocker.patch("adapters.ctags.sys")
    mock_sys.frozen = False

    # Mock __file__ to return a known path
    with patch("adapters.ctags.__file__", "/some/path/adapters/ctags.py"):
        result = _get_base_path()
        # Should return parent.parent, which is /some/path
        assert result == Path("/some/path")


@pytest.mark.unit
@pytest.mark.mock
def test_get_base_path_pyinstaller_frozen(mocker):
    """_get_base_path should return _MEIPASS when frozen."""
    mock_sys = mocker.patch("adapters.ctags.sys")
    mock_sys.frozen = True
    mock_sys._MEIPASS = "/tmp/pyinstaller_extracted"

    result = _get_base_path()

    assert result == Path("/tmp/pyinstaller_extracted")


@pytest.mark.unit
@pytest.mark.mock
def test_get_base_path_pyinstaller_no_meipass(mocker):
    """_get_base_path should fallback to __file__.parent when frozen but no _MEIPASS."""
    # Create a mock that doesn't auto-create _MEIPASS
    mock_sys = MagicMock(spec=["frozen"])
    mock_sys.frozen = True
    # _MEIPASS is not in spec, so getattr will return default
    mocker.patch("adapters.ctags.sys", mock_sys)

    # Mock __file__ fallback
    with patch("adapters.ctags.__file__", "/some/path/adapters/ctags.py"):
        result = _get_base_path()
        # Should use Path(__file__).parent as fallback since _MEIPASS doesn't exist
        assert result == Path("/some/path/adapters")


# ============================================================================
# Tests for _normalize_system
# ============================================================================


@pytest.mark.unit
@pytest.mark.mock
@pytest.mark.parametrize(
    "system_input,expected",
    [
        ("Darwin", "macos"),
        ("darwin", "macos"),
        ("DARWIN", "macos"),
        ("Linux", "linux"),
        ("linux", "linux"),
        ("Windows", "windows"),
        ("windows", "windows"),
    ],
)
def test_normalize_system_various_inputs(mocker, system_input, expected):
    """_normalize_system should normalize system names correctly."""
    mock_platform = mocker.patch("adapters.ctags.platform")
    mock_platform.system.return_value = system_input

    result = _normalize_system()

    assert result == expected


@pytest.mark.unit
@pytest.mark.mock
def test_normalize_system_case_insensitive(mocker):
    """_normalize_system should handle case-insensitive input."""
    mock_platform = mocker.patch("adapters.ctags.platform")
    mock_platform.system.return_value = "DARWIN"

    result = _normalize_system()

    assert result == "macos"


# ============================================================================
# Tests for _normalize_architecture
# ============================================================================


@pytest.mark.unit
@pytest.mark.mock
@pytest.mark.parametrize(
    "system,machine,expected",
    [
        ("macos", "arm64", "arm64"),
        ("macos", "ARM64", "arm64"),
        ("macos", "aarch64", "arm64"),
        ("macos", "x86_64", "x86_64"),
        ("macos", "AMD64", "x86_64"),
        ("linux", "aarch64", "aarch64"),
        ("linux", "arm64", "aarch64"),
        ("linux", "ARM", "aarch64"),
        ("linux", "x86_64", "x86_64"),
        ("windows", "arm64", "aarch64"),
        ("windows", "aarch64", "aarch64"),
        ("windows", "x86_64", "x86_64"),
    ],
)
def test_normalize_architecture_various_combinations(mocker, system, machine, expected):
    """_normalize_architecture should normalize architecture correctly for different systems."""
    mock_platform = mocker.patch("adapters.ctags.platform")
    mock_platform.machine.return_value = machine

    result = _normalize_architecture(system)

    assert result == expected


@pytest.mark.unit
@pytest.mark.mock
def test_normalize_architecture_macos_arm(mocker):
    """macOS ARM should normalize to arm64."""
    mock_platform = mocker.patch("adapters.ctags.platform")
    mock_platform.machine.return_value = "arm64"

    result = _normalize_architecture("macos")

    assert result == "arm64"


@pytest.mark.unit
@pytest.mark.mock
def test_normalize_architecture_linux_arm(mocker):
    """Linux ARM should normalize to aarch64."""
    mock_platform = mocker.patch("adapters.ctags.platform")
    mock_platform.machine.return_value = "aarch64"

    result = _normalize_architecture("linux")

    assert result == "aarch64"


@pytest.mark.unit
@pytest.mark.mock
def test_normalize_architecture_x86_64(mocker):
    """x86_64 should remain x86_64 for all systems."""
    mock_platform = mocker.patch("adapters.ctags.platform")
    mock_platform.machine.return_value = "x86_64"

    assert _normalize_architecture("macos") == "x86_64"
    assert _normalize_architecture("linux") == "x86_64"
    assert _normalize_architecture("windows") == "x86_64"


@pytest.mark.unit
@pytest.mark.mock
def test_normalize_architecture_case_insensitive(mocker):
    """_normalize_architecture should handle case-insensitive machine names."""
    mock_platform = mocker.patch("adapters.ctags.platform")
    mock_platform.machine.return_value = "ARM64"

    result = _normalize_architecture("macos")

    assert result == "arm64"


# ============================================================================
# Tests for _build_binary_pattern
# ============================================================================


@pytest.mark.unit
@pytest.mark.parametrize(
    "system,arch,expected",
    [
        ("macos", "arm64", "ctags-macos-arm64-*"),
        ("macos", "x86_64", "ctags-macos-x86_64-*"),
        ("linux", "aarch64", "ctags-linux-aarch64-*"),
        ("linux", "x86_64", "ctags-linux-x86_64-*"),
        ("windows", "x86_64", "ctags-windows-x86_64-*.exe"),
        ("windows", "arm64", "ctags-windows-arm64-*.exe"),
    ],
)
def test_build_binary_pattern_various_platforms(system, arch, expected):
    """_build_binary_pattern should generate correct patterns for all platforms."""
    result = _build_binary_pattern(system, arch)

    assert result == expected


@pytest.mark.unit
def test_build_binary_pattern_windows_has_exe():
    """Windows patterns should include .exe extension."""
    result = _build_binary_pattern("windows", "x86_64")

    assert result.endswith(".exe")
    assert "ctags-windows-x86_64-" in result


@pytest.mark.unit
def test_build_binary_pattern_non_windows_no_exe():
    """Non-Windows patterns should not include .exe extension."""
    for system in ["macos", "linux"]:
        result = _build_binary_pattern(system, "x86_64")
        assert not result.endswith(".exe")
        assert result.startswith("ctags-")


# ============================================================================
# Tests for get_ctags_path
# ============================================================================


@pytest.mark.unit
@pytest.mark.mock
def test_get_ctags_path_single_match(mocker, tmp_path):
    """get_ctags_path should return the binary when one match is found."""
    # Setup mocks
    mock_base_path = tmp_path
    bin_dir = mock_base_path / "bin"
    bin_dir.mkdir(parents=True)

    # Create a matching binary
    binary_path = bin_dir / "ctags-macos-arm64-2025.11.27"
    binary_path.touch()

    mocker.patch("adapters.ctags._get_base_path", return_value=mock_base_path)
    mocker.patch("adapters.ctags._normalize_system", return_value="macos")
    mocker.patch("adapters.ctags._normalize_architecture", return_value="arm64")

    result = get_ctags_path()

    assert result == binary_path


@pytest.mark.unit
@pytest.mark.mock
def test_get_ctags_path_multiple_matches_selects_latest(mocker, tmp_path):
    """get_ctags_path should select the alphabetically last binary when multiple exist."""
    # Setup mocks
    mock_base_path = tmp_path
    bin_dir = mock_base_path / "bin"
    bin_dir.mkdir(parents=True)

    # Create multiple matching binaries
    binary1 = bin_dir / "ctags-macos-arm64-2025.10.01"
    binary2 = bin_dir / "ctags-macos-arm64-2025.11.27"
    binary3 = bin_dir / "ctags-macos-arm64-2025.09.15"
    binary1.touch()
    binary2.touch()
    binary3.touch()

    mocker.patch("adapters.ctags._get_base_path", return_value=mock_base_path)
    mocker.patch("adapters.ctags._normalize_system", return_value="macos")
    mocker.patch("adapters.ctags._normalize_architecture", return_value="arm64")

    result = get_ctags_path()

    # Should select the alphabetically last (most recent version)
    assert result == binary2


@pytest.mark.unit
@pytest.mark.mock
def test_get_ctags_path_windows_exe(mocker, tmp_path):
    """get_ctags_path should handle Windows .exe binaries correctly."""
    # Setup mocks
    mock_base_path = tmp_path
    bin_dir = mock_base_path / "bin"
    bin_dir.mkdir(parents=True)

    # Create Windows binary
    binary_path = bin_dir / "ctags-windows-x86_64-p6.2.20251130.0.exe"
    binary_path.touch()

    mocker.patch("adapters.ctags._get_base_path", return_value=mock_base_path)
    mocker.patch("adapters.ctags._normalize_system", return_value="windows")
    mocker.patch("adapters.ctags._normalize_architecture", return_value="x86_64")

    result = get_ctags_path()

    assert result == binary_path
    assert result.name.endswith(".exe")


@pytest.mark.unit
@pytest.mark.mock
def test_get_ctags_path_no_matches_raises_error(mocker, tmp_path):
    """get_ctags_path should raise FileNotFoundError when no binary matches."""
    # Setup mocks
    mock_base_path = tmp_path
    bin_dir = mock_base_path / "bin"
    bin_dir.mkdir(parents=True)

    # Don't create any matching binaries

    mocker.patch("adapters.ctags._get_base_path", return_value=mock_base_path)
    mocker.patch("adapters.ctags._normalize_system", return_value="macos")
    mocker.patch("adapters.ctags._normalize_architecture", return_value="arm64")

    with pytest.raises(FileNotFoundError) as exc_info:
        get_ctags_path()

    assert "No ctags binary found" in str(exc_info.value)
    assert "ctags-macos-arm64-*" in str(exc_info.value)


@pytest.mark.unit
@pytest.mark.mock
def test_get_ctags_path_bin_dir_not_exists(mocker, tmp_path):
    """get_ctags_path should raise FileNotFoundError when bin directory doesn't exist."""
    # Setup mocks
    mock_base_path = tmp_path
    # Don't create bin directory

    mocker.patch("adapters.ctags._get_base_path", return_value=mock_base_path)
    mocker.patch("adapters.ctags._normalize_system", return_value="macos")
    mocker.patch("adapters.ctags._normalize_architecture", return_value="arm64")

    with pytest.raises(FileNotFoundError) as exc_info:
        get_ctags_path()

    assert "No ctags binary found" in str(exc_info.value)


@pytest.mark.unit
@pytest.mark.mock
def test_get_ctags_path_integration_workflow(mocker, tmp_path):
    """Integration test: complete workflow from system detection to binary selection."""
    # Setup real directory structure
    mock_base_path = tmp_path
    bin_dir = mock_base_path / "bin"
    bin_dir.mkdir(parents=True)

    # Create binaries for different platforms
    linux_binary = bin_dir / "ctags-linux-x86_64-2025.11.27"
    macos_binary = bin_dir / "ctags-macos-arm64-2025.11.27"
    windows_binary = bin_dir / "ctags-windows-x86_64-p6.2.20251130.0.exe"
    linux_binary.touch()
    macos_binary.touch()
    windows_binary.touch()

    # Test macOS ARM64
    mocker.patch("adapters.ctags._get_base_path", return_value=mock_base_path)
    mocker.patch("adapters.ctags._normalize_system", return_value="macos")
    mocker.patch("adapters.ctags._normalize_architecture", return_value="arm64")

    result = get_ctags_path()
    assert result == macos_binary

    # Test Linux x86_64
    mocker.patch("adapters.ctags._normalize_system", return_value="linux")
    mocker.patch("adapters.ctags._normalize_architecture", return_value="x86_64")

    result = get_ctags_path()
    assert result == linux_binary

    # Test Windows x86_64
    mocker.patch("adapters.ctags._normalize_system", return_value="windows")
    mocker.patch("adapters.ctags._normalize_architecture", return_value="x86_64")

    result = get_ctags_path()
    assert result == windows_binary
