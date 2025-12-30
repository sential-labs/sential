"""
Ctags binary management and path resolution.

This module handles locating and managing the platform-specific ctags binary
that is bundled with the application.
"""

import sys
import platform
from pathlib import Path


def _get_base_path() -> Path:
    """Get the base path for bundled binaries (handles PyInstaller)."""
    if getattr(sys, "frozen", False):
        # PyInstaller sets _MEIPASS when frozen
        return Path(getattr(sys, "_MEIPASS", Path(__file__).parent))  # type: ignore[attr-defined]
    return Path(__file__).parent


def _normalize_system() -> str:
    """Normalize platform system name to match binary naming convention."""
    raw_system = platform.system().lower()
    return "macos" if raw_system == "darwin" else raw_system


def _normalize_architecture(system: str) -> str:
    """Normalize machine architecture to match binary naming convention."""
    machine = platform.machine().lower()
    if "arm" in machine or "aarch64" in machine:
        return "arm64" if system == "macos" else "aarch64"
    return "x86_64"


def _build_binary_pattern(system: str, arch: str) -> str:
    """Build glob pattern to match ctags binary regardless of version."""
    # Pattern: ctags-{system}-{arch}-* or ctags-{system}-{arch}-*.exe
    if system == "windows":
        return f"ctags-{system}-{arch}-*.exe"
    return f"ctags-{system}-{arch}-*"


def get_ctags_path() -> str:
    """
    Locate the ctags binary for the current platform.

    Searches for binaries matching the pattern: ctags-{system}-{arch}-{version}
    This allows version-agnostic binary selection while preserving version info in filenames.

    Returns:
        str: Full path to the ctags binary

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

    return str(selected)

