# Codebase Guide

## 1. Project Entry Point & Orchestration

### Overview

The entry point of Sential is located in `main.py`. This module implements a Typer-based CLI that orchestrates the entire lifecycle of a context bridge generation—from initial repository validation to the final synthesis of an onboarding guide.

Sential is designed around a **two-phase generation architecture**:
1.  **The Architect**: Analyzes the project structure and symbols to create a "syllabus" (a plan of chapters).
2.  **The Builder**: Uses the syllabus to read specific file contents and generate high-fidelity documentation.

The CLI acts as the conductor for this pipeline, managing user interactions, configuration, and the hand-off between different core subsystems.

### Command Structure and Initialization

The CLI is built using the `typer` library, with `main.py` defining the primary `app` and its main entry point.

-   **Entry Point**: The `main()` function handles the top-level logic. It accepts a `--path` (defaulting to the current working directory) and an optional `--language` flag.
-   **Validation**: It uses `SubprocessGitClient` from `adapters.git` to ensure the target directory is a valid Git repository. Sential relies heavily on the Git index for performance and to respect `.gitignore` rules.
-   **Interactive Selection**: If the language is not provided via the CLI, `make_language_selection()` uses the `inquirer` library to prompt the user. This ensures the tool operates within the bounds of supported language heuristics defined in `constants.SupportedLanguage`.

### Configuration Management

Sential requires an LLM (Large Language Model) to act as both the Architect and the Builder. Configuration for the model name and API key is managed via:

-   `get_config_file()` / `save_config()`: Helper functions located in `core.llm` that persist settings to a local config file.
-   `edit_model_config()`: Triggered via the `--configure` flag, allowing users to update their API credentials and model preferences (e.g., switching between different OpenAI or Anthropic models via `litellm`).

### The Scanning Pipeline

Once initialized, `main.py` executes the scanning pipeline described in the `ARCHITECTURE.md`:

1.  **Inventory Generation**: It retrieves a full list of tracked files using `git_client.get_file_paths_list()`.
2.  **Categorization**: The `categorize_files()` function (from `core.categorization`) applies the "Language Sieve." It filters the thousands of raw Git files into "Language" files (source code) and "Context" files (READMEs, manifests like `package.json` or `pyproject.toml`).
3.  **Content Processing**: `process_files()` (from `core.processing`) reads the actual content and extracts symbols.
4.  **Payload Aggregation**: A `FilesystemFileWriter` is used to stream this data into a temporary JSONL file. This payload includes the original prompt, processed file metadata, and the raw file paths.

### Architect and Builder Execution

The final stage of the CLI execution transitions from local file scanning to LLM-powered synthesis:

-   **Prompt Construction**: The CLI reads the `SYLLABUS_GENERATION_PROMPT` from `core.prompts`.
-   **The Architect Phase**: It calls `ask_llm()` with the collected context. The LLM acts as "The Architect," returning a JSON syllabus that maps conceptual chapters (e.g., "Authentication Flow") to specific file paths.
-   **Syllabus Parsing**: `parse_syllabus_response()` validates and structures the LLM's output.
-   **The Builder Phase**: Finally, `process_syllabus_result()` (from `core.doc_generator`) iterates through the syllabus. For each chapter, it gathers the full text of the referenced files and prompts the LLM to write the detailed documentation.

### Error Handling Strategy

As a CLI tool, Sential prioritizes user-friendly feedback over raw stack traces. `main.py` implements several specialized error handlers:

-   `print_temp_file_err()`: For filesystem permission or disk space issues during payload generation.
-   `print_file_io_err()`: For failures when reading source code or writing the final `ONBOARDING.md`.
-   `print_unexpected_err()`: A catch-all handler that provides diagnostic information and reporting instructions.

### Key Symbols and Files

-   `main.py`: The orchestrator and CLI definition.
-   `pyproject.toml`: Defines the environment, including dependencies like `rich` for UI, `inquirer` for prompts, and `litellm` for API abstraction.
-   `FilesystemFileWriter`: A utility to manage the streaming of large repository metadata into temporary storage.
-   `SupportedLanguage`: An enum that drives the language-specific heuristics used throughout the scan.

## 2. System Core Models & Constants

### Overview

The core of Sential's intelligence lies in how it categorizes and evaluates the "significance" of files within a codebase. Rather than treating all files as equal, the system uses a heuristic-driven model to identify project roots, entry points, and high-value documentation.

This logic is primarily split between `models.py` and `core/models.py`, which define the data structures, and `constants.py`, which contains the expert-system rules for various programming languages.

### Language Heuristics

The system supports multiple languages (Python, JS/TS, Java, C#, Go, C/C++) defined in the `SupportedLanguage` enum. Each language is associated with a `LanguagesHeuristics` object in `constants.py`. These heuristics are the primary drivers for the discovery pipeline:

- **Manifests**: Files like `package.json` or `pyproject.toml` that define project boundaries.
- **Extensions**: Valid source code extensions (e.g., `.tsx`, `.java`).
- **Signals**: Filenames that indicate high-importance logic or entry points (e.g., `main`, `app`, `index`).
- **Ignore Directories**: Standard paths that usually contain noise or non-production code (e.g., `node_modules`, `tests`, `htmlcov`).

### File Classification and Scoring

The `FileMetadata` class in `core/models.py` is the central container for a file's lifecycle during discovery. When a file is encountered, Sential computes several derived attributes in `__post_init__` to facilitate fast matching:

- `name_lower`: The filename (e.g., `readme.md`).
- `suffix_lower`: The extension (e.g., `.py`).
- `depth`: How deep the file is in the directory tree (used to penalize files deep in subdirectories).
- `file_parents`: A set of directory names in the path, used to check against `ignore_dirs`.

#### File Categories
Files are assigned a `FileCategory` which dictates how they are handled in the final output:
- `CONTEXT`: High-level project intent (e.g., `README.md`, `.cursorrules`).
- `MANIFEST`: Dependency and configuration files (e.g., `requirements.txt`).
- `SIGNAL`: Key architectural files or entry points.
- `SOURCE`: Standard source code files.
- `CHAPTER_FILE`: Specific files used for structured documentation generation.
- `UNKNOWN`: Files that don't match specific high-value patterns.

### The "Soul" of a Project: Universal Context

In `constants.py`, the `UNIVERSAL_CONTEXT_FILES` tuple defines what the codebase refers to as the "soul" of a project. These are files that provide high-signal intent regardless of the programming language. 
- **Documentation**: `architecture.md`, `design.md`.
- **AI Rules**: `.cursorrules`, `.windsurfrules`, `claude.md`.
- **Infrastructure**: `Dockerfile`, `docker-compose.yml`, `Makefile`.

These files are prioritized because they explain the *why* and *how* of a project, which is often more valuable for LLM context than raw source code.

### Code Symbol Extraction (Ctags)

For source code analysis, Sential relies on `Ctag` models. These represent specific symbols (classes, functions, etc.) extracted via Universal Ctags. 

To prevent token bloat, `constants.py` defines `CTAGS_KINDS`. This whitelist ensures only relevant architectural symbols are processed:
- **Core Logic**: `class`, `method`, `function`.
- **Data Structures**: `struct`, `interface`, `type`, `enum`.
- **Hierarchy**: `namespace`, `module`, `package`.

### Data Flow Containers

Once files are processed and categorized, they are managed using specialized containers:
- `ProcessedFile`: A frozen dataclass representing the final state of a file (path, type, and content).
- `CategoryProcessedFiles`: A helper class that groups `ProcessedFile` instances by their `FileCategory`, facilitating the organization of the final technical documentation or context package.

## 3. External Adapters: Git & Universal Ctags

### Overview

The codebase relies on two primary mechanisms for understanding the structure and content of a project: **Git** for file discovery and **Universal Ctags** for structural analysis.

The system treats a repository not just as a flat list of files, but as a hierarchical set of symbols. By using `git` as the source of truth for file enumeration, the tool respects the developer's environment (ignoring `.gitignore` files). By using `ctags`, the tool extracts a high-level "map" of source code—identifying functions, classes, and variables—without needing to parse full file contents into the LLM context, which saves significantly on token usage.

---

### File Discovery via Git

The `adapters/git.py` module acts as a high-level wrapper around the Git CLI. It is designed to be memory-efficient, using streaming subprocesses to handle repositories with tens of thousands of files.

#### Key Components

- **`SubprocessGitClient`**: The primary implementation. It uses `git ls-files` with specific flags:
    - `--cached`: Includes tracked files.
    - `--others`: Includes untracked files.
    - `--exclude-standard`: Respects `.gitignore`, `.git/info/exclude`, and global ignores.
- **`GitClient` Protocol**: Defines the interface (`is_repo`, `count_files`, `get_file_paths_list`), allowing the system to swap the real Git client for a `MockGitClient` during testing.

#### Design Decisions

- **Streaming for Efficiency**: In `count_files`, the code uses `subprocess.Popen` with `stdout=subprocess.PIPE` and iterates over the stream directly. This prevents the application from loading a massive list of file paths into memory at once just to count them.
- **Verification**: The `is_repo` method uses `git rev-parse --is-inside-work-tree`. This is the standard, lightweight way to verify a directory is a valid Git repository without checking for the existence of a `.git` folder (which might be in a parent directory).

---

### Structural Analysis via Ctags

Once files are discovered, the system uses `ctags` to index source code. This is handled by a combination of binary management (`adapters/ctags.py`) and extraction logic (`core/ctags_extraction.py`).

#### Binary Management (`adapters/ctags.py`)
To ensure portability, the project bundles platform-specific `universal-ctags` binaries. 
- **Auto-detection**: `get_ctags_path()` detects the OS and architecture (e.g., `macos-arm64`, `linux-x86_64`) and resolves the correct bundled binary in the `bin/` directory.
- **PyInstaller Support**: `_get_base_path` accounts for "frozen" environments (compiled executables), where resources are extracted to a temporary `_MEIPASS` directory.

#### Extraction Logic (`core/ctags_extraction.py`)
This module orchestrates the execution of the `ctags` binary and parses its JSON output.

- **`extract_ctags_for_source_files`**: This is the main entry point. It processes files in batches (defaulting to 100) to keep the subprocess arguments manageable and allows for incremental token budget checking.
- **`_run_ctags`**: Executes the binary with specific flags:
    - `--output-format=json`: Allows for robust parsing compared to the legacy tag format.
    - `--fields=+n`: Ensures line numbers are included (though currently, primarily symbol names and kinds are used).
    - `-f -`: Directs output to `stdout` for streaming.
- **`_parse_tag_line`**: Safely parses each line of JSON. It filters symbols based on `CTAGS_KINDS` (defined in `constants.py`) to ensure only relevant structural symbols (like classes and functions) are kept.

#### Token Budget Integration
A critical feature of the extraction process is its integration with the `TokenBudget`. As `ctags` output is generated for each file:
1. The length of the generated symbol list is converted to a token count.
2. The `token_budget.can_afford(token_usage)` check is performed.
3. If the budget is exhausted, extraction stops immediately, ensuring the tool never produces a context that exceeds LLM limits.

---

### Design Patterns and Technicalities

#### 1. The Adapter Pattern
The use of `GitClient` (Protocol) and the separate `ctags` adapter follows the Adapter pattern. This decouples the core logic from the specific CLI tools. If the project were to switch from `universal-ctags` to a Language Server Protocol (LSP) based approach or from `git` to a native library like `libgit2`, the changes would be isolated to these adapter files.

#### 2. Robust Subprocess Handling
In `_run_ctags`, the `subprocess.Popen` call uses `errors="replace"` and `encoding="utf-8"`. This is a "staff-level" detail: source code repositories often contain files with broken or unusual encodings. Without `errors="replace"`, the entire discovery process would crash if `ctags` encountered a non-UTF-8 character in a symbol name or file path.

#### 3. Batching and State
The extraction process maintains a `current_index` and returns it alongside the processed files. This allows the system to resume or stop gracefully. The `CategoryProcessedFiles` object is updated in-place, acting as a collector for the results of the discovery phase.

### Connection to the Rest of the System
The output of this module—specifically `ProcessedFile` objects containing strings of tags (e.g., "function my_func\nclass MyClass")—is passed forward to the formatting and ingestion layers. These tags serve as a "compressed" version of the source code, providing the LLM with the "what" and "where" of the codebase without the "how" (the implementation details), effectively mapping the architecture for the model.

## 4. File Categorization & Intelligence

### Overview

The core logic of the codebase analysis revolves around two primary concerns: **categorization** (determining what a file is and how important it is) and **I/O management** (safely reading from the source and writing results to disk). 

These operations are handled in `core/categorization.py` and `core/file_io.py`. Together, they transform a raw list of file paths into a structured, prioritized dataset that the system uses to build context for LLMs.

### File Categorization and Significance

The module `core/categorization.py` is responsible for sifting through the codebase to identify which files provide the most architectural value. This is a heuristic-driven process that avoids processing irrelevant noise (like binary files or deep nested tests) while prioritizing entry points and manifests.

#### The Categorization Pipeline
The primary entry point is `categorize_files`. It takes a list of `Path` objects and returns a dictionary grouping `FileMetadata` by their `FileCategory`.

- **Heuristics Engine**: It relies on `LANGUAGES_HEURISTICS` (imported from `constants.py`) to understand language-specific patterns (e.g., that `.py` files are source code for Python, while `package.json` is a manifest for JavaScript).
- **Progress Reporting**: The function integrates with the `ui.progress_display` module. It calculates progress in 10% increments to provide smooth feedback to the user during large scans.

#### Scoring Logic
The function `calculate_significance` implements a tiered scoring system. The final score is used to rank files, where a higher score implies higher relevance for context generation.

1.  **Base Score by Category**:
    - `FileCategory.CONTEXT` (1000 pts): Highest priority. Includes `README.md`, `.cursorrules`, and other global documentation.
    - `FileCategory.MANIFEST` (80 pts): Configuration files like `requirements.txt`, `pom.xml`, or `.csproj`.
    - `FileCategory.SIGNAL` (60 pts): Main entry points (e.g., `main.py`, `index.ts`).
    - `FileCategory.SOURCE` (50 pts): Standard logic files.
    - `FileCategory.UNKNOWN` (0 pts): Files that don't match the target language's extensions.

2.  **Path Depth Penalty**: 
    Architectural files are typically closer to the root. The system applies a penalty of `-5` points for every directory level beyond the root (`depth > 1`). For example, `src/app/main.py` is penalized more than `main.py`.

3.  **Ignore Penalties**:
    If a file exists within a directory matched by `ignore_dirs` (e.g., `tests/`, `mocks/`, `examples/`), it receives a heavy `-100` point penalty. This effectively pushes tests and mocks to the bottom of the significance list or results in a negative score.

### File I/O Management

The `core/file_io.py` module abstracts filesystem interactions through a set of Protocols (`FileReader` and `FileWriter`). This design decision decouples the business logic from the actual filesystem, enabling robust unit testing through mocks.

#### Reading Files
The `FilesystemFileReader` handles the extraction of source code. 
- **Safety**: It includes a `_is_binary_file` check that reads the first 1024 bytes for null bytes (`\0`). This prevents the system from attempting to read images, compiled binaries, or PDFs as text.
- **Resilience**: It uses `encoding="utf-8"` with `errors="ignore"` to ensure that files with minor encoding issues don't crash the entire analysis process.

#### Writing and Temp Files
The `FilesystemFileWriter` is more specialized, designed to handle the various ways the system persists analysis results.
- **Factory Methods**: It provides multiple ways to instantiate a writer:
    - `from_path(file_path)`: For specific output locations.
    - `from_tempfile(suffix)`: Creates a randomly named temporary file.
    - `from_named_tempfile(name)`: Creates a predictable file in the system temp directory.
- **JSONL Support**: Since the system often processes many files, it uses the JSON Lines format. The `append_jsonl_line` and `append_processed_files` methods allow the system to stream results to disk incrementally, reducing memory overhead.

#### Testing Utilities
This module provides `MockFileReader` and `MockFileWriter`. These are not just basic mocks; they include inspection attributes like `read_file_calls` and `written_jsonl_lines`. This allows engineers to write tests that verify exactly which files were read and what data was written without ever touching the actual disk.

### Design Decisions

- **Protocol-based I/O**: By using `typing.Protocol`, the codebase follows the Dependency Inversion Principle. The core logic depends on the *interface* of a reader/writer, not the concrete filesystem implementation.
- **Negative Scoring for Ignores**: Rather than strictly excluding "ignored" directories (which might contain a rare piece of useful context), the system penalizes them by -100. This allows the file to exist in the metadata but ensures it is ranked lower than even the most basic source file.
- **Shallow-file Bias**: The assumption that files closer to the root are "more architectural" is a common heuristic in software mapping. This bias helps the LLM see `app.py` before it sees `src/utils/string_helpers.py`.
- **Fast Binary Check**: Reading only the first 1024 bytes for a null byte is a performance optimization. It avoids reading a 50MB binary file into memory just to realize it's not text.

## 5. Token Management & Budgeting

### Overview

The `core/tokens.py` module is responsible for managing the "economy" of text data processed by the system. In LLM-based applications, managing token counts is critical for both staying within model context windows and controlling API costs. 

This module provides two primary abstractions:
1.  **Token Counting**: Tools to calculate how many tokens a specific string contains using model-specific encodings.
2.  **Budget Management**: Logic to enforce limits on how many tokens can be processed, often categorized by the "importance" or type of the file being extracted (e.g., source code vs. documentation).

### Token Counting

Token counting is abstracted through the `TokenCounter` protocol, allowing the system to swap between real counting and mocks during testing.

#### Tiktoken Implementation
The `TiktokenCounter` class is the production-ready implementation. It uses OpenAI's `tiktoken` library to ensure accuracy for specific models.
- **Model Selection**: By default, it targets `gpt-4o`. 
- **Graceful Fallback**: If a provided model name is unrecognized, it falls back to the `cl100k_base` encoding, which is the standard for most modern GPT models.
- **Safety**: The `count` method handles `None` or empty strings gracefully, returning `0`.

#### Testing Utilities
To avoid heavy dependencies and network calls during unit tests, the `NoOpTokenCounter` allows engineers to provide fixed values or custom logic for counting without actually performing tokenization.

---

### Budget Management and Strategies

The codebase treats tokens as a finite resource that must be allocated strategically across different file types. This is managed via the `TokenBudget` protocol.

#### TokenLimits and File Categories
The `TokenLimits` dataclass defines the global policy for token distribution. It uses the `FileCategory` enum (from `core.models`) to assign weightings:
- **CONTEXT (10%)**: High-level project context.
- **MANIFEST (5%)**: Configuration and structural data.
- **SIGNAL (5%)**: Key indicators or metadata.
- **SOURCE (40%)**: Actual source code content.

*Note: The remaining percentage allows for overhead or unallocated buffer.*

#### PooledTokenBudget
The `PooledTokenBudget` is the most sophisticated budget manager. It implements a "progressive unlock" strategy:
- **Initialization**: It calculates an `initial_allocation` for every category based on the `max_total` (default 200,000) and the category ratios.
- **Dynamic Pool**: Instead of strict silos, it uses a cumulative pool. When `start_category(category)` is called, the budget allocated for that category is added to the shared `pool`.
- **Spending**: Files can "spend" tokens from this pool. This allows for flexibility; if one category uses fewer tokens than its ratio allows, those tokens remain in the pool for subsequent categories.

#### FixedTokenBudget
A simpler implementation, `FixedTokenBudget`, is used for capping specific runs (like a single chapter or a batch operation). It uses a simple `max_tokens * ctx_ratio` calculation to set a hard limit that does not care about file categories.

---

### Design Decisions

#### Protocols for Dependency Injection
By defining `TokenCounter` and `TokenBudget` as `typing.Protocol` classes, the system follows the Dependency Inversion Principle. The extraction logic depends on the interface, not the implementation. This is why you will see `MockTokenBudget` used extensively in the test suites—it records calls to `spend` and `can_afford` so tests can assert that the extraction logic correctly respects the limits without needing to set up a real `tiktoken` environment.

#### Immutable Policies
`TokenLimits` is marked as `frozen=True`. This ensures that once a budget policy is defined for an extraction task, it cannot be modified mid-run, preventing "budget creep" and making the system's behavior more predictable.

#### Statefulness
While `TokenLimits` is immutable, the `TokenBudget` implementations (like `PooledTokenBudget`) are highly stateful. They act as trackers throughout the lifecycle of a file extraction process. A typical flow looks like this:
1.  Identify the category of files being processed.
2.  Call `start_category(cat)` to "fund" the pool.
3.  For each file:
    -   Calculate tokens via a `TokenCounter`.
    -   Check `can_afford(count)`.
    -   If true, process the file and call `spend(count)`.

## 6. The Processing Pipeline

### Overview

The processing and generation layer is responsible for converting raw file metadata and content into structured information that the LLM can use to generate technical documentation. This stage is governed by two primary concerns: **priority-based extraction** and **token budget management**.

The logic is split between `core/processing.py`, which handles the reading and transformation of files (including specialized handling like ctags), and `core/doc_generator.py`, which orchestrates the final LLM calls to assemble the documentation.

### Processing Workflow

The system processes files in a strict order defined in `process_files`. This order ensures that the most foundational context (like READMEs and manifests) is prioritized before diving into specific source code.

#### 1. Prioritization and Categorization
Files are handled according to the `FileCategory` enum in the following sequence:
1.  `CONTEXT`: General project info (e.g., `README.md`).
2.  `MANIFEST`: Dependency and configuration files (e.g., `package.json`, `pyproject.toml`).
3.  `SIGNAL`: Entry points or high-level architecture files.
4.  `SOURCE`: Individual source code files.

Within each category, files are sorted by their `score` (significance) and `depth` (proximity to the root). This ensures that if a token budget is reached, the system has already captured the most "important" files in that category.

#### 2. Extraction Strategies
There are two distinct paths for processing content:
-   **Standard Reading:** For `CONTEXT`, `MANIFEST`, and `SIGNAL` files, the system uses `process_readable_files_for_category`. This simply reads the full text of the file using a `FileReader` (typically `FilesystemFileReader`).
-   **Ctags Extraction:** For `SOURCE` files, the system uses `extract_ctags_for_source_files` (defined in `core/ctags_extraction`). This is a crucial optimization: instead of sending massive source files to the LLM, the system extracts structural information (classes, functions, variables) to stay within token limits while preserving architectural context.

### Token Budget Management

Budgeting is enforced throughout the processing lifecycle to prevent API errors and manage costs. The system uses two types of budgets defined in `core/tokens`:

-   **`PooledTokenBudget`**: Used during the initial analysis phase. It manages limits across different categories of files.
-   **`FixedTokenBudget`**: Used during the chapter generation phase in `process_chapter_files`. It sets a hard limit (e.g., 200,000 tokens) for the content provided to the LLM for a single chapter.

The `TokenCounter` (specifically `TiktokenCounter` for OpenAI models) is used to calculate the usage of a file's content *before* it is added to the processing queue. If `token_budget.can_afford(token_usage)` returns false, processing for that category stops to avoid exceeding the limit.

### Documentation Generation

Once the files are processed, `core/doc_generator.py` handles the synthesis of the final Markdown document.

#### Syllabus Execution
The generation process is driven by a `SyllabusResult`, which contains a project overview and a list of chapters.
-   **File Resolution:** For each chapter, `process_chapter_files` reads the specific files associated with that chapter's scope.
-   **Payload Assembly:** The system combines the project context, the chapter-specific prompt, and the processed file contents using `build_chapter_payload`.
-   **LLM Interaction:** The `ask_llm` function sends the payload to the configured model. Note that the generator includes a `sleep(15)` between chapters to respect API rate limits.
-   **Incremental Writing:** The `FilesystemFileWriter` writes chapters to the output file (usually `Overview.md`) in append mode (`"a"`), ensuring that the document is built progressively.

### Key Components

-   **`process_files` (`core/processing.py`):** The entry point for the analysis phase. It coordinates sorting, budgeting, and the choice of extraction logic.
-   **`process_readable_files_for_category`:** A helper that iterates through files, checks budgets, and handles `FileReadError` gracefully (logging a warning via `rich` while continuing the loop).
-   **`process_syllabus_result` (`core/doc_generator.py`):** The main loop for the generation phase. It transforms a high-level syllabus into a sequence of LLM requests and file writes.
-   **`RichProgressDisplay` (`ui/progress_display.py`):** Integrated into the processing loops to provide real-time feedback in the terminal as files are read and analyzed.

### Design Decisions

-   **Resilience:** Both processing functions wrap file I/O in `try/except` blocks for `FileReadError`. This prevents a single corrupt or missing file from crashing the entire documentation pipeline.
-   **Order Matters:** By processing `CONTEXT` and `MANIFEST` first, the system builds a "mental model" of the project that informs how subsequent source code is interpreted.
-   **Token Safety:** The use of `islice` and budget checks ensures the system is "token-aware" at every step, which is vital when dealing with large codebases that could otherwise exceed LLM context windows.

## 7. LLM Integration & Prompting

### Overview

The LLM (Large Language Model) integration layer is the cognitive engine of this project. It is responsible for transforming raw codebase data—such as file listings, ctags, and source code—into structured, meaningful documentation.

This area is divided into two primary concerns:
1.  **Communication and Configuration (`core/llm.py`):** Handling the interface with external LLM providers and managing local configuration.
2.  **Prompt Engineering and Orchestration (`core/prompts.py`):** Defining the complex instructions that guide the LLM through a two-stage process: first, analyzing the repository to create a "Syllabus," and second, generating detailed documentation for individual chapters.

### LLM Interfacing and Configuration

The `core/llm.py` module serves as a thin wrapper around the `litellm` library. This choice allows the system to remain model-agnostic, supporting various providers (OpenAI, Anthropic, etc.) through a unified interface.

#### Key Functions
- `ask_llm(model_name, api_key, prompt)`: The primary execution point. It sends a prompt to the LLM with a system role and includes a default `num_retries=3` to handle transient API failures.
- `save_config(model, api_key)`: Persists user credentials and preferences to `~/.sential/settings.json`. It utilizes the `FilesystemFileWriter` (from `core.file_io`) to ensure the directory and file are created correctly.
- `get_config_file()`: Retrieves the stored configuration using `FilesystemFileReader`.

### Syllabus Generation Strategy

The generation of documentation starts with the "Syllabus" phase. Instead of dumping the entire codebase into a single prompt, the system first asks the LLM to act as a staff engineer and plan the documentation structure.

The `SYLLABUS_GENERATION_PROMPT` in `core/prompts.py` instructs the LLM to:
1.  **Analyze the Payload:** Review context files (READMEs), manifests (`package.json`), and file paths.
2.  **Summarize Context:** Produce a 2–4 paragraph `project_context` that grounds all future prompts.
3.  **Identify Themes:** Determine logical chapters (e.g., "Database Layer", "API Routing").
4.  **Map Files:** Assign specific file paths from the repository to each chapter.

#### Parsing the Syllabus
The `parse_syllabus_response()` function is a robust parser for the LLM's output. It handles common LLM behaviors, such as wrapping JSON in Markdown code blocks, and performs validation to ensure the output matches the `SyllabusResult` and `SyllabusChapter` dataclasses. Crucially, it resolves relative strings into actual `Path` objects and filters out any paths that do not exist on the local disk.

### Chapter Documentation Workflow

Once a syllabus is generated, the system moves to generating the actual content for each chapter. This is managed by a templating system that ensures consistency across different LLM calls.

#### Modular Prompt Construction
The prompt for a specific chapter is built using `build_chapter_prompt()`, which pulls together several modular constants:
- `AUDIENCE_AND_GOAL`: Sets the persona (Staff Engineer) and target audience (New Hire).
- `CHAPTER_STYLE_GUIDE`: Enforces strict Markdown formatting rules (no H2s, specific H3 headers, fenced code blocks).
- `CHAPTER_COVERAGE`: Directs the LLM to focus on specific symbols, design decisions, and system connections.

#### Payload Assembly
The `build_chapter_payload()` function is the final step before calling the LLM. It takes the generated prompt and appends the actual content of the files associated with that chapter. It uses a clear separator format:
```text
--- File: path/to/file.py ---
[File Content]
```
This structured format allows the LLM to accurately attribute code logic to specific files in the repository.

### Design Decisions

- **Two-Pass Architecture:** By separating syllabus generation from chapter writing, the system overcomes context window limitations and ensures that the final documentation is cohesive rather than a disjointed collection of file summaries.
- **Strict JSON Output:** The syllabus phase requires a strict JSON response. This allows the Python core to programmatically decide which files to read next, making the documentation process dynamic based on the project's actual structure.
- **Stateless Prompts:** Each chapter prompt is designed to be self-contained by injecting the `project_context` into every call. This ensures that even if chapters are processed in parallel, they all share the same high-level understanding of the project.
- **Filesystem Abstraction:** Using `FilesystemFileReader` and `FilesystemFileWriter` within the config logic maintains consistency with how the rest of the core handles I/O, allowing for easier testing or potential future abstractions of the storage layer.

## 8. Terminal UI & Progress Reporting

### Overview

The progress reporting system provides a decoupled, stateful way to visualize long-running operations in the CLI. Rather than allowing business logic to depend directly on UI libraries, the system uses a **Protocol-based abstraction**. This ensures that core logic (like processing files or calling APIs) can report its status without knowing whether that status is being rendered as a vibrant terminal progress bar, written to a log file, or suppressed entirely during unit tests.

The system is split into two layers:
1.  **Low-level UI Utilities (`ui/progress.py`)**: Thin wrappers around the `rich` library.
2.  **High-level Abstraction (`ui/progress_display.py`)**: A formal interface and multiple implementations (Rich, No-op) that manage the lifecycle of a task.

---

### Progress Protocols and Interfaces

#### The `ProgressDisplay` Protocol
Defined in `ui/progress_display.py`, this `Protocol` acts as the structural contract for any component that reports progress. It follows a strict lifecycle designed to be used as a context manager:

1.  `__enter__`: Prepares the display environment (e.g., starting a Rich live display).
2.  `on_start(description, total)`: Initializes a specific task with a goal.
3.  `on_update(advance, description)`: Incrementally moves the progress bar or updates the status text.
4.  `on_complete(description, completed, total)`: Finalizes the task visual.
5.  `__exit__`: Cleans up resources.

#### Implementations
-   **`RichProgressDisplay`**: The primary implementation used in the CLI. It handles the "lazy" creation of the progress bar and ensures the UI is only active when needed.
-   **`NoOpProgressDisplay`**: A critical utility for the test suite. It implements the same interface but performs no actions, preventing terminal pollution and dependency issues during CI/CD or unit testing.

---

### The Low-Level Rich Wrapper

The file `ui/progress.py` serves as the engine for terminal visuals. It standardizes how progress looks across the entire application using the `rich` library.

#### `ProgressState`
An enumeration that maps logical states to semantic colors:
-   `IN_PROGRESS` (Magenta)
-   `COMPLETE` (Green)
-   `WARNING` (Yellow)
-   `ERROR` (Red)

#### Key Functions
-   `create_progress()`: Configures a `rich.progress.Progress` instance with a specific column layout: a `SpinnerColumn` for activity, a `TextColumn` for descriptions, a `BarColumn` for the visual bar, and a `TaskProgressColumn` for percentages.
-   `update_progress()`: A unified updater. A design constraint here is that **state and description must be updated together**. If you change the state to `COMPLETE`, you must provide the final description so the function can apply the correct color formatting (e.g., `[green]Processing complete`).

---

### Design Decisions

#### 1. Decoupling via Protocols
By using `typing.Protocol` instead of an abstract base class, we achieve structural subtyping. Business logic modules only need to accept a type that "looks like" a `ProgressDisplay`. This allows us to inject a `NoOpProgressDisplay` in tests or a `LoggingProgressDisplay` in headless environments without changing a single line of business logic.

#### 2. Context Manager Lifecycle
The `RichProgressDisplay` requires usage as a context manager:
```python
with RichProgressDisplay() as progress:
    progress.on_start("Indexing...", total=100)
    # ... logic ...
    progress.on_update(advance=1)
    progress.on_complete("Done!", completed=100)
```
This pattern ensures that the `rich` terminal "Live" display is properly started and stopped, even if an exception occurs during the logic execution.

#### 3. State-Based Styling
The system enforces that visual styling (colors) is tied to the `ProgressState`. Developers do not manually pass hex codes or color names; they pass a state, and the `update_progress` utility handles the Rich-specific string formatting (e.g., `[magenta]Task Name`).

#### 4. Indeterminate Progress
The `total` parameter in `on_start` and `create_task` is optional (`int | None`). If passed as `None`, the UI automatically renders an indeterminate "pulsing" bar, which is useful for operations where the final count isn't known upfront (e.g., streaming a response or traversing a directory tree).

---

### Integration Guide

When implementing a new long-running service:
1.  Accept a `ProgressDisplay` instance in the constructor or method.
2.  Use the `on_update` method's flexibility:
    -   `on_update(advance=n)`: Move the bar without changing text.
    -   `on_update(description="...")`: Change text without moving the bar.
    -   `on_update(advance=n, description="...")`: Do both simultaneously.
3.  Always ensure `on_start` is called before updates, or the `RichProgressDisplay` will raise a `RuntimeError`.

## 9. Testing Philosophy & Infrastructure

### Overview

The Sential codebase adheres to a rigorous testing philosophy that prioritizes **testability through design**. Rather than relying on complex monkey-patching or heavy integration tests, the system is built using architectural patterns—specifically Dependency Injection and Protocol-based interfaces—that make unit testing straightforward and isolated.

The testing infrastructure is built on `pytest` and is organized to mirror the source directory structure, ensuring that every core component has a corresponding test suite.

### Design Principles for Testability

To maintain a high level of testability, the codebase follows four core principles:

- **Dependency Injection**: External dependencies (I/O, subprocesses, token counting) are never hardcoded inside functions. They are passed as arguments, allowing tests to swap real implementations for mocks.
- **Protocol-Based Interfaces**: Using `typing.Protocol`, the system defines clear interfaces for dependencies like `TokenCounter` or `ProgressDisplay`. This decouples the logic from specific implementations.
- **Optional UI/External Dependencies**: UI components are typically optional parameters with sensible defaults. In production, they provide rich CLI output; in tests, they default to "no-op" (no operation) versions.
- **Factory Functions**: For operations involving global state or external binaries (like `subprocess.Popen`), functions accept a factory callable. This allows tests to inject a mock factory that returns a pre-configured mock process.

### Mock and No-Op Implementations

The codebase distinguishes between two types of test doubles:

#### No-Op Implementations
These are used when a dependency is required but its behavior is irrelevant to the specific test. They return sensible defaults and have no side effects.
- `NoOpTokenCounter` (in `core/tokens.py`): Always returns a fixed token count.
- `NoOpProgressDisplay` (in `ui/progress_display.py`): Silently accepts progress updates without printing to the console.

#### Mock Implementations
These are used when the test needs to verify *how* a dependency was interacted with.
- `MockTokenBudget`: Tracks calls to `spend()` and `can_afford()` to ensure the logic respects token limits.
- `TrackingProgressDisplay`: Records calls to `on_start`, `on_update`, and `on_complete` to verify that UI feedback is correctly triggered during long-running tasks.

### Core Test Components

#### Shared Fixtures (`tests/core/conftest.py`)
Shared fixtures provide a consistent environment across the suite. Key fixtures include:
- `project_root`: A `tmp_path` based directory for file I/O tests.
- `mock_popen_factory`: A utility to simulate `ctags` execution by yielding predefined JSON lines to `stdout`.
- `token_budget` and `token_counter`: Pre-configured test doubles for resource management tests.

#### Categorization Tests (`tests/core/test_categorization.py`)
This suite validates the heuristic engine. It heavily utilizes `@pytest.mark.parametrize` to test:
- **Scoring Rules**: Ensuring files like `README.md` get high scores while files in `tests/` directories receive penalties.
- **Language Specifics**: Verifying that `package.json` is a manifest for JavaScript but not for Python.
- **Depth Penalties**: Confirming that the significance score decreases as files move deeper into the directory tree.

#### Ctags Extraction Tests (`tests/core/test_ctags_extraction.py`)
This suite focuses on the integration with the external `universal-ctags` binary:
- **Parsing Logic**: Tests `_parse_tag_line` against valid and malformed JSON.
- **Batch Processing**: Ensures that `_run_ctags` correctly handles batches of files and recovers from subprocess errors.
- **Budget Integration**: Verifies that `extract_ctags_for_source_files` stops processing immediately if the `TokenBudget` is exhausted.

### Navigating the Tests

New engineers should look to the following files for reference when adding features:

1.  **Adding a new heuristic**: Add cases to `test_categorization.py`. Follow the pattern of providing a `Path` and `SupportedLanguage` and asserting the expected significance score.
2.  **Modifying I/O logic**: Use the `mock_file_reader_factory` in `conftest.py` to simulate file contents without hitting the disk.
3.  **Extending the UI**: Use the `tracking_progress_display` fixture to ensure your new logic correctly updates the user on its progress.

Tests are categorized using markers:
- `@pytest.mark.unit`: Fast, isolated logic tests.
- `@pytest.mark.mock`: Tests requiring patched behaviors or tracked interactions.
- `@pytest.mark.integration`: Slower tests that might exercise multiple modules together.

