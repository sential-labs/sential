# Sential

**Sential is Source Available. It is free for personal use and open for contribution. For commercial use in teams > 3, please [contact us](mailto:florin@sential.ai) or see LICENSE.**

Sential is a local-first tool designed to generate high-signal context bridges from Git repositories. It helps developers quickly understand codebases by intelligently filtering and extracting the most relevant code symbols and context files, then synthesizing comprehensive onboarding guides through a sophisticated two-phase architecture.

## Overview

Sential operates as a CLI tool that scans your Git repository and creates a structured "bridge" of context that can be fed to LLMs for better code understanding. Unlike standard RAG (Retrieval-Augmented Generation) approaches used by tools like Cursor—which are optimized for search queries but poor at synthesis—Sential uses a hierarchical two-phase approach specifically designed for generating comprehensive onboarding documentation.

The tool combines:

- **Language-specific heuristics** to identify important files
- **Universal Ctags** for extracting code symbols (classes, functions, definitions)
- **Git-aware filtering** to respect your `.gitignore` and focus on relevant modules
- **Monorepo support** with interactive module selection
- **Two-phase generation**: The Architect (global planning) + The Builder (detailed writing)

## How It Works

### The Problem with Standard RAG

Traditional code understanding tools (like Cursor) use RAG with sparse retrieval:

- They chunk your code into vectors and search for relevant snippets
- When you ask a question, they retrieve the top 20 chunks (maybe 5% of your codebase)
- **The flaw**: They miss the "glue"—they see function bodies but miss class definitions, folder structure, and system-wide patterns

This works great for search ("Where is the login function?") but fails at synthesis ("Explain how the whole authentication system works").

### Sential's Solution: The Architect & The Builder

Instead of a linear chain that degrades quality, Sential uses a **hierarchical two-pass approach** that maintains high fidelity while staying within context limits.

#### Phase 1: The Architect (Global Context)

**Goal**: Create a structured syllabus without writing content.

**Input**:

- The Ctags map (code structure)
- README.md and manifest files (project intent)
- Package files (technology stack)

**Process**:
The Architect analyzes the entire project structure and identifies core systems (e.g., Authentication, Data Ingestion, API Layer). It generates a JSON syllabus with chapters, each mapped to specific file paths.

**Output**: A structured plan like:

```json
[
  {
    "title": "Chapter 1: The Authentication Flow",
    "files": ["src/auth/AuthController.ts", "src/middleware/jwt.ts"]
  },
  {
    "title": "Chapter 2: Data Ingestion Pipeline",
    "files": ["src/workers/ingest.ts", "src/models/DataPoint.ts"]
  }
]
```

#### Phase 2: The Builder (Local Context)

**Goal**: Write high-fidelity content for each chapter.

**Input**:

- The chapter definition from Phase 1
- The **full content** of the specific files listed for that chapter

**Process**:
For each chapter, the Builder receives only the relevant files needed for that specific topic. It writes detailed explanations with full context, without noise from unrelated parts of the codebase.

**Output**: A complete markdown section for each chapter, compiled into a comprehensive onboarding guide.

### Why This Approach Works

✅ **Precision**: Each chapter is written with only the relevant files in context—no noise from unrelated modules

✅ **Parallelizable**: Chapters can be generated simultaneously (great for local GPU or high rate limits)

✅ **Self-Correcting**: The Builder can identify missing dependencies (e.g., "I also need User.ts") using import analysis

✅ **Incremental**: You can regenerate individual chapters when code changes, without reprocessing the entire codebase

✅ **High Fidelity**: Unlike linear summarization chains, each chapter maintains full context of its specific domain

### The Complete Pipeline

1. **Discovery**: Scan Git repository, identify modules, filter by language
2. **Extraction**: Generate Ctags map (code symbols) + read context files (README, manifests)
3. **Architect Phase**: Analyze structure → Generate chapter syllabus
4. **Builder Phase**: For each chapter → Read specific files → Write detailed content
5. **Artifact**: Output comprehensive `ONBOARDING.md` guide

The generated onboarding guide serves as both:

- **Documentation** for new team members
- **Reference** for implementation work and feature planning

## Features

- 🎯 **Smart Filtering**: Automatically identifies and prioritizes high-signal files using language-specific heuristics
- 🔍 **Symbol Extraction**: Uses Universal Ctags to extract structural code symbols without full implementation details
- 📦 **Monorepo Support**: Interactive module selection for large codebases
- 🚀 **Local-First**: All processing happens locally; your code never leaves your machine
- ⚡ **Fast**: Leverages Git index for efficient file discovery
- 🏗️ **Two-Phase Generation**: Architect phase creates structured syllabus, Builder phase writes detailed chapters
- 📚 **Comprehensive Artifacts**: Generates complete onboarding guides that serve as both documentation and implementation reference
- 🔄 **Incremental Updates**: Regenerate individual chapters when code changes, without full reprocessing

## Installation

### Prerequisites

- Python 3.11 or higher
- Git (for repository scanning)

### Install from Source

Clone the repository and install in development mode:

```bash
# Clone the repository
git clone <repository-url>
cd sential

# Install in development mode with all dependencies
pip install -e ".[dev]"
```

This will install:
- All production dependencies (typer, inquirer, tiktoken, rich)
- Development dependencies (pytest, pytest-mock, pytest-cov, pytest-xdist)

### Development Setup

For development, you can install with just the dev dependencies:

```bash
pip install -e ".[dev]"
```

Then run tests:

```bash
# Run all tests
pytest

# Run tests with coverage
pytest --cov

# Run tests in parallel
pytest -n auto
```

### Building Standalone Executable

To build a standalone executable using PyInstaller:

```bash
python build.py
```

This creates a single-file executable named `sential` that includes all dependencies and the ctags binaries.

## Usage

```bash
# Scan current directory and generate onboarding guide
sential --path . --language Python

# Scan specific repository
sential --path /path/to/repo --language JavaScript

# Generate onboarding guide from existing scan
sential generate --payload scan.jsonl
```

The tool will:

1. Scan your repository and extract code structure
2. Run the Architect phase to create a chapter syllabus
3. Run the Builder phase to write detailed content for each chapter
4. Output a comprehensive `ONBOARDING.md` file

The generated guide serves as both onboarding documentation and a reference for ongoing implementation work.

## Supported Languages

- Python
- JavaScript/TypeScript
- Go
- Java
- C#

## Architecture

See [ARCHITECTURE.md](ARCHITECTURE.md) for detailed technical specifications.

## License

This project is licensed under the Business Source License 1.1 (BUSL 1.1). See [LICENSE](LICENSE) for details.

**Key Points:**

- ✅ Free for personal, non-commercial use
- ✅ Open for contributions
- ✅ Automatically converts to Apache 2.0 on January 1, 2029
- ⚠️ Commercial use in teams > 3 requires a license

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

### Development Setup

1. Fork the repository and clone it locally
2. Install in development mode:
   ```bash
   pip install -e ".[dev]"
   ```
3. Run tests to ensure everything works:
   ```bash
   pytest
   ```
4. Make your changes and ensure tests pass
5. Submit a Pull Request

### Project Structure

The project uses `pyproject.toml` for configuration, which includes:
- Project metadata and dependencies
- Pytest configuration for testing
- Coverage settings
- Build system configuration

All dependencies are managed through `pyproject.toml` - there's no need to manually manage `requirements.txt`.

## Contact

For commercial licensing inquiries, please [contact us](mailto:florin@sential.ai).
