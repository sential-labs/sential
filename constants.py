"""
Application-wide constants and configuration mappings.

This module defines the core heuristics and configuration data used throughout
the Sential CLI application. It includes language-specific manifest and extension
definitions, ctags symbol kind filters, and universal context file patterns.
"""

from typing import Final, Mapping
from models import SupportedLanguage, LanguagesHeuristics


# Language-specific heuristics for module discovery and file filtering.
# This mapping associates each supported programming language with its
# characteristic manifest files and source code extensions. It is used by
# the discovery pipeline to identify modules and filter files during scanning.
# The manifests are used to detect module roots (directories containing projects),
# while extensions are used to filter source code files for ctags processing.
LANGUAGES_HEURISTICS: Final[Mapping[SupportedLanguage, LanguagesHeuristics]] = {
    SupportedLanguage.PY: {
        "manifests": frozenset(
            {
                "requirements.txt",
                "pyproject.toml",
                "setup.py",
                "pipfile",
                "tox.ini",
            }
        ),
        "extensions": frozenset({".py", ".pyi"}),
    },
    SupportedLanguage.JS: {
        "manifests": frozenset(
            {
                "package.json",
                "deno.json",
                "yarn.lock",
                "pnpm-lock.yaml",
                "next.config.js",
                "vite.config.js",
                "tsconfig.json",
            }
        ),
        "extensions": frozenset(
            {".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs", ".vue", ".svelte"}
        ),
    },
    SupportedLanguage.JAVA: {
        "manifests": frozenset(
            {
                "pom.xml",  # Maven
                "build.gradle",  # Gradle (Groovy)
                "build.gradle.kts",  # Gradle (Kotlin)
                "settings.gradle",
                "mvnw",  # Maven Wrapper
                "gradlew",  # Gradle Wrapper
            }
        ),
        "extensions": frozenset({".java", ".kt", ".scala", ".groovy"}),
    },
    SupportedLanguage.CS: {
        "manifests": frozenset(
            {
                ".csproj",
                ".sln",
                ".fsproj",
                ".vbproj",
                "global.json",
                "nuget.config",
            }
        ),
        "extensions": frozenset({".cs", ".fs", ".vb", ".cshtml", ".razor"}),
    },
    SupportedLanguage.GO: {
        "manifests": frozenset(
            {
                "go.mod",
                "go.sum",
                "go.work",
                "main.go",
            }
        ),
        "extensions": frozenset({".go"}),
    },
    SupportedLanguage.CPP: {
        "manifests": frozenset(
            {
                "cmakelists.txt",
                "makefile",
                "configure.ac",
                "meson.build",
                "conanfile.txt",
                "vcpkg.json",
                ".gitmodules",
            }
        ),
        "extensions": frozenset(
            {
                ".c",
                ".cpp",
                ".h",
                ".hpp",
                ".cc",
                ".hh",
                ".cxx",
                ".hxx",
                ".m",
                ".mm",
            }
        ),
    },
}

# Set of ctags symbol kinds that are extracted and included in the output.
# This set defines which types of code symbols (classes, functions, etc.) are
# considered valuable for context generation. Symbols with kinds not in this
# set are filtered out during ctags processing to reduce noise and token usage.
# The set includes:
# - Core logic symbols: class, method, function
# - Data structures: struct, enum, union, interface, typedef, type
# - Hierarchy symbols: namespace, module, package
CTAGS_KINDS: Final[frozenset[str]] = frozenset(
    {
        # The Core Logic
        "class",
        "method",
        "function",
        # The Data Structures
        "struct",
        "enum",
        "union",
        "interface",
        "typedef",
        "type",
        # The Hierarchy (Crucial for C#/C++)
        "namespace",
        "module",
        "package",
    }
)

# Universal context files that define the "soul" of a project.
# This tuple contains filenames (case-insensitive) that are considered high-value
# context files regardless of the target programming language. These files are
# always included in the context extraction phase and are prioritized during
# output generation. They include documentation, AI-specific instructions, and
# infrastructure configuration files.
UNIVERSAL_CONTEXT_FILES: Final[tuple[str, ...]] = (
    # Documentation & Intent (The "Why")
    "readme.md",
    "readme.txt",
    "architecture.md",
    "contributing.md",
    "design.md",
    # AI Specific Instructions (The "How" - Extremely High Signal)
    "claude.md",
    ".cursorrules",
    ".windsurfrules",
    # Environment / Config Templates (The "Infrastructure")
    ".env.example",
    ".env.template",
    "docker-compose.yml",
    "dockerfile",
    "makefile",
    "justfile",
    "rakefile",
    "procfile",
)
