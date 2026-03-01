"""
Build script for creating a standalone executable using PyInstaller.

This script bundles the CLI application and its dependencies (including ctags binaries)
into a single executable file.
"""

import platform
import PyInstaller.__main__  # type: ignore

SEPARATOR = ";" if platform.system() == "Windows" else ":"

PyInstaller.__main__.run(
    ["main.py", "--onefile", f"--add-data=bin{SEPARATOR}bin", "--name=sential"]
)
