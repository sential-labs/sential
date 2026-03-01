"""
Sential CLI Entry Point.

This module implements the main command-line interface for Sential, a tool designed
to generate high-signal context bridges from local Git repositories. It orchestrates
the scanning pipeline by filtering files based on language-specific heuristics,
scoping the scan to specific modules (monorepo support), and aggregating both
raw file content (for context) and code symbols (via Universal Ctags).

The pipeline operates in four distinct stages:

1.  **Validation & Selection**: Verifies the target path is a valid Git repository
    and handles interactive user selection for the target programming language and
    application scopes (modules).
2.  **Inventory Generation**: Streams the Git index to separate files into 'Language'
    (source code) and 'Context' (manifests/docs) buckets using the "Language Sieve"
    approach defined in `constants.py`.
3.  **Content Extraction**: Reads high-priority context files in full (with intelligent
    truncation) to establish the repository's configuration and documentation baseline.
4.  **Symbol Extraction**: Pipes source files through Universal Ctags to extract structural
    code symbols (classes, functions, definitions) without including full implementation
    details, optimizing token usage for downstream consumption.

Usage:
    Run directly as a script or via the installed entry point.

    $ python main.py --path /path/to/repo --language Python

Dependencies:
    - Typer: CLI argument parsing and app structure.
    - Rich: Terminal UI, colors, and progress visualization.
    - Inquirer: Interactive terminal user prompts.
    - Universal Ctags: External engine used for symbol extraction.
"""

from pathlib import Path
from typing import Annotated
import json
import typer
from rich import print as pr
import inquirer  # type: ignore
from inquirer.themes import GreenPassion  # type: ignore
from adapters.git import SubprocessGitClient
from constants import SupportedLanguage
from core.doc_generator import process_syllabus_result
from core.exceptions import (
    FileIOError,
    FileWriteError,
    InvalidFilePathError,
    TempFileError,
)
from core.file_io import FilesystemFileReader, FilesystemFileWriter
from core.llm import ask_llm, get_config_file, save_config
from core.prompts import SYLLABUS_GENERATION_PROMPT, parse_syllabus_response
from core.processing import process_files
from core.categorization import categorize_files

app = typer.Typer()


@app.command()
def main(
    path: Annotated[
        Path,
        typer.Option(
            exists=True,  # Typer throws error if path doesn't exist
            file_okay=False,  # Typer throws error if it's a file, not a dir
            dir_okay=True,  # Must be a directory
            resolve_path=True,  # Automatically converts to absolute path
            help="Root path from which Sential will start identifying modules",
        ),
    ] = Path.cwd(),  # If not provided, use the current working directory
    language: Annotated[
        str | None,
        typer.Option(help=f"Available languages: {', '.join(list(SupportedLanguage))}"),
    ] = None,
    configure: Annotated[
        bool,
        typer.Option(
            "--configure",
            "-c",
            help="Edit model and API key configuration (shows current values for editing).",
        ),
    ] = False,
):
    """
    The main entry point for the Sential CLI application.

    This function orchestrates the entire scanning process. It validates that the
    provided path is a valid Git repository, determines the programming language
    (either via arguments or user prompt), allows the user to select specific
    application scopes (modules), and generates a final JSONL payload containing
    context files and code symbols (ctags).

    Args:
        path (Path): The root directory of the codebase to scan. Must be an existing
            directory and a valid Git repository. Defaults to the current working directory.
        language (str): The target programming language for the scan. If not provided
            via CLI arguments, the user will be prompted to select one interactively.

    Raises:
        typer.Exit: If the path is not a git repository or if an unsupported language is selected.
    """
    if configure:
        edit_model_config()
        raise typer.Exit(0)

    # Validate path is git repository
    git_client = SubprocessGitClient(path)
    if not git_client.is_repo():
        pr(f"[red]Error:[/red] Not a git repository: [green]'{path}'[/green]")
        raise typer.Exit(code=1)

    # Validate language passed by user
    # If not passed, open language selection
    try:
        language = normalize_language(language)
    except ValueError:
        if language is not None:
            pr(f"\n[red bold]Not a valid language: {language}")
        language = make_language_selection()

    pr(f"\n[green]Language selected: {language}...[/green]\n")
    pr(f"[green]Scanning: {path}...[/green]\n")

    try:
        fw = FilesystemFileWriter.from_named_tempfile("sential_payload")
    except TempFileError as e:
        print_temp_file_err(e)
        return

    config = get_config_file()

    model = config.get("model")
    api_key = config.get("api_key")

    if not model or not api_key:
        make_model_selection()
        config = get_config_file()
        model = config.get("model")
        api_key = config.get("api_key")

    try:
        prompt_data = {"type": "prompt", "content": SYLLABUS_GENERATION_PROMPT}
        fw.write_file(json.dumps(prompt_data) + "\n", mode="w")

        files_in_path = git_client.count_files()
        file_paths_list = git_client.get_file_paths_list()

        categorized_files = categorize_files(file_paths_list, files_in_path, language)

        processed_files = process_files(path, categorized_files)
        fw.append_processed_files(processed_files)

        file_paths_data = {
            "type": "file_paths",
            "paths": [str(p) for p in file_paths_list],
        }
        fw.append_jsonl_line(file_paths_data)
        if fw.file_path:
            prompt = FilesystemFileReader().read_file(fw.file_path)
            resp = ask_llm(model, api_key, prompt)
            syllabus_data = parse_syllabus_response(resp, path)
            process_syllabus_result(path, syllabus_data)
    except TempFileError as e:
        print_temp_file_err(e)
    except (FileWriteError, InvalidFilePathError) as e:
        print_file_io_err(e)
    except Exception as e:  # noqa: BLE001
        # Catch-all for any unexpected errors - ensures users always see
        # a friendly message instead of a raw Python stack trace
        print_unexpected_err(e)


def normalize_language(language: str | None) -> SupportedLanguage:
    """
    Normalizes and validates a language string to a SupportedLanguage enum value.

    Performs case-insensitive matching against the supported languages and returns
    the matching enum value. If no language is provided (None or empty string) or
    the string doesn't match any supported language, raises ValueError.

    Args:
        language (str | None): The language string to normalize. Can be None,
            empty, or a string representation of a supported language.

    Returns:
        SupportedLanguage: The matching SupportedLanguage enum value.

    Raises:
        ValueError: If no language is provided (None or empty string) or if the
            provided language string doesn't match any supported language
            (case-insensitive).
    """
    if not language:
        raise ValueError("No language provided")

    normalized = language.strip().lower()
    for lang in SupportedLanguage:
        if str(lang).lower() == normalized:
            return lang
    raise ValueError(f"Unsupported language: {language}")


def print_temp_file_err(e: TempFileError) -> None:
    """
    Displays a user-friendly error message for temporary file operation failures.

    Prints formatted error messages to inform the user about workspace/temporary
    file issues, including diagnostic information for troubleshooting. This helps
    users understand and resolve filesystem permission or disk space problems.

    Args:
        e (TempFileError): The exception that was raised, containing error details
            and diagnostic information.

    Raises:
        typer.Exit: Always raises with exit code 1 to terminate the application.
    """
    pr("❌ [bold red]Workspace Error[/bold red]")
    pr("The app couldn't create the temporary files needed to run.")
    pr(
        "\n[yellow]Quick Fix:[/yellow] Ensure your temp folder is writable and you have free disk space."
    )

    pr("\n--- PLEASE REPORT THIS ---")
    pr(f"Error Context: {e}")
    pr(f"Diagnostics: {e.diagnostic_info}")
    raise typer.Exit(code=1) from e


def print_file_io_err(e: FileIOError) -> None:
    """
    Displays a user-friendly error message for file I/O operation failures.

    Prints formatted error messages to inform the user about file read/write
    issues, including the file path and diagnostic information for troubleshooting.

    Args:
        e (FileIOError): The exception that was raised, containing error details
            and file path information.

    Raises:
        typer.Exit: Always raises with exit code 1 to terminate the application.
    """
    pr("❌ [bold red]File I/O Error[/bold red]")
    pr(f"The app encountered an error while working with files: {e.message}")
    if e.file_path:
        pr(f"File path: [yellow]{e.file_path}[/yellow]")

    pr("\n[yellow]Quick Fix:[/yellow] Check file permissions and available disk space.")
    if e.original_exception:
        pr(f"\nTechnical details: {e.original_exception}")

    raise typer.Exit(code=1) from e


def print_unexpected_err(e: Exception) -> None:
    """
    Displays a user-friendly error message for unexpected errors.

    This catch-all handler ensures that any unhandled exceptions are presented
    to the user in a friendly way, rather than showing a raw Python stack trace.
    It provides helpful guidance and diagnostic information for reporting issues.

    Args:
        e (Exception): The unexpected exception that was raised.

    Raises:
        typer.Exit: Always raises with exit code 1 to terminate the application.
    """
    pr("❌ [bold red]Unexpected Error[/bold red]")
    pr("An unexpected error occurred while processing your request.")
    pr(f"\n[yellow]Error Type:[/yellow] {type(e).__name__}")
    pr(f"[yellow]Error Message:[/yellow] {str(e)}")

    pr("\n[yellow]What to do:[/yellow]")
    pr("1. Check that your repository is valid and accessible")
    pr("2. Ensure you have sufficient disk space and permissions")
    pr("3. Try running the command again")
    pr("4. If the problem persists, please report this issue")

    pr("\n--- PLEASE REPORT THIS ---")
    pr(f"Error Type: {type(e).__name__}")
    pr(f"Error Message: {e}")
    if hasattr(e, "__cause__") and e.__cause__:
        pr(f"Caused by: {e.__cause__}")

    raise typer.Exit(code=1) from e


def make_language_selection() -> SupportedLanguage:
    """
    Interactively prompts the user to select a supported programming language.
    This is invoked when the user does not provide the `--language` argument via the CLI.
    It displays a list of languages defined in `SupportedLanguages`.

    Returns:
    SupportedLanguages: The enum member corresponding to the user's selection.
    """

    pr(
        "\n[bold green]Select the programming language for which to generate the bridge.[/bold green]"
    )

    questions = [
        inquirer.List(
            "language",
            message="Hit [ENTER] to make your selection",
            choices=list(SupportedLanguage),
        ),
    ]

    answers = inquirer.prompt(questions, theme=GreenPassion())

    if not answers:

        raise typer.Exit()

    return SupportedLanguage(answers["language"])


def make_model_selection() -> None:
    """
    Interactively prompts the user for model name and API key, then saves them
    via save_config. Blocks until both values are entered and config is saved.
    On any error or cancellation, prints a message and exits the process.
    """
    pr("\n[bold green]Configure model and API key.[/bold green]\n")

    questions = [
        inquirer.Text("model", message="Enter model name"),
        inquirer.Text("api_key", message="Enter API key"),
    ]

    answers = inquirer.prompt(questions, theme=GreenPassion())

    if not answers:
        raise typer.Exit(code=1)

    model = (answers.get("model") or "").strip()
    api_key = (answers.get("api_key") or "").strip()

    if not model or not api_key:
        pr("\n[bold][red]Error:[/bold] Model name and API key are required.")
        raise typer.Exit(code=1)

    try:
        save_config(model, api_key)
    except (FileWriteError, InvalidFilePathError) as e:
        print_file_io_err(e)
    except OSError as e:
        pr("[red]Error:[/red] Could not save config.")
        pr(f"[yellow]{e}[/yellow]")
        raise typer.Exit(code=1) from e

    pr("[green]Config saved.[/green]\n")


def edit_model_config() -> None:
    """
    Interactively prompts for model name and API key with current config
    prepopulated, so the user can edit and save. Same flow as make_model_selection
    but with existing values as defaults. On cancel or invalid input, exits.
    """
    config = get_config_file()
    current_model = (config.get("model") or "").strip()
    current_api_key = (config.get("api_key") or "").strip()

    pr("\n[bold green]Edit model and API key.[/bold green]\n")

    questions = [
        inquirer.Text("model", message="Enter model name", default=current_model),
        inquirer.Text("api_key", message="Enter API key", default=current_api_key),
    ]

    answers = inquirer.prompt(questions, theme=GreenPassion())

    if not answers:
        raise typer.Exit(code=1)

    model = (answers.get("model") or "").strip()
    api_key = (answers.get("api_key") or "").strip()

    if not model or not api_key:
        pr("\n[bold][red]Error:[/bold] Model name and API key are required.")
        raise typer.Exit(code=1)

    try:
        save_config(model, api_key)
    except (FileWriteError, InvalidFilePathError) as e:
        print_file_io_err(e)
    except OSError as e:
        pr("[red]Error:[/red] Could not save config.")
        pr(f"[yellow]{e}[/yellow]")
        raise typer.Exit(code=1) from e

    pr("[green]Config saved.[/green]\n")


if __name__ == "__main__":
    app()
