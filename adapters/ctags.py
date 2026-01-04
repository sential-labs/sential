"""
Ctags binary management and path resolution.

This module handles locating and managing the platform-specific ctags binary
that is bundled with the application.
"""

import sys
import platform
from pathlib import Path


def _get_base_path() -> Path:
    """
    Get the base path for bundled binaries, handling PyInstaller packaging.

    When running as a PyInstaller bundle, the actual application files are
    extracted to a temporary directory. This function detects that scenario
    and returns the appropriate base path for locating bundled resources.

    Returns:
        Path: The base directory path where bundled resources are located.
            In PyInstaller bundles, this is sys._MEIPASS. Otherwise, it's
            the parent directory of this module (to access the bin/ directory).
    """
    if getattr(sys, "frozen", False):
        # PyInstaller sets _MEIPASS when frozen
        return Path(getattr(sys, "_MEIPASS", Path(__file__).parent))  # type: ignore[attr-defined]
    return Path(__file__).parent.parent


def _normalize_system() -> str:
    """
    Normalize the platform system name to match binary naming convention.

    Converts platform.system() output to match the naming convention used
    for bundled ctags binaries. Specifically, "Darwin" is normalized to "macos".

    Returns:
        str: The normalized system name ("macos", "linux", "windows").
    """
    raw_system = platform.system().lower()
    return "macos" if raw_system == "darwin" else raw_system


def _normalize_architecture(system: str) -> str:
    """
    Normalize the machine architecture to match binary naming convention.

    Detects ARM/AArch64 architectures and normalizes them to match the naming
    convention used for bundled ctags binaries. macOS ARM is "arm64", while
    Linux ARM is "aarch64".

    Args:
        system: The normalized system name (from _normalize_system).

    Returns:
        str: The normalized architecture name ("arm64", "aarch64", or "x86_64").
    """
    machine = platform.machine().lower()
    if "arm" in machine or "aarch64" in machine:
        return "arm64" if system == "macos" else "aarch64"
    return "x86_64"


def _build_binary_pattern(system: str, arch: str) -> str:
    """
    Build a glob pattern to match ctags binary filenames regardless of version.

    Creates a glob pattern that matches the ctags binary naming convention:
    `ctags-{system}-{arch}-{version}` or `ctags-{system}-{arch}-{version}.exe`
    for Windows. The version part is wildcarded to allow version-agnostic selection.

    Args:
        system: The normalized system name (e.g., "macos", "linux", "windows").
        arch: The normalized architecture name (e.g., "arm64", "x86_64").

    Returns:
        str: A glob pattern string that matches ctags binaries for the platform.
    """
    # Pattern: ctags-{system}-{arch}-* or ctags-{system}-{arch}-*.exe
    if system == "windows":
        return f"ctags-{system}-{arch}-*.exe"
    return f"ctags-{system}-{arch}-*"


def get_ctags_path() -> Path:
    """
    Locate the ctags binary for the current platform.

    Searches for binaries matching the pattern: ctags-{system}-{arch}-{version}
    This allows version-agnostic binary selection while preserving version info in filenames.

    Returns:
        Path: Full path to the ctags binary

    Raises:
        FileNotFoundError: If no matching binary is found
    """
    base_path = _get_base_path()
    bin_dir = base_path / "bin"

    system = _normalize_system()
    arch = _normalize_architecture(system)
    pattern = _build_binary_pattern(system, arch)

    # Search for matching binaries (version-agnostic)
    matches = list(bin_dir.glob(pattern))

    if not matches:
        raise FileNotFoundError(
            f"No ctags binary found matching pattern '{pattern}' in {bin_dir}"
        )

    if len(matches) > 1:
        # If multiple versions exist, prefer the most recent (alphabetically last)
        matches.sort()
        selected = matches[-1]
        # Could log a warning here if desired
    else:
        selected = matches[0]

    return selected
