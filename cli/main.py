"""
This is a simple CLI tool that receives a path to a folder and lists all the files in it.
"""

import json
import os
import subprocess
import tempfile
from typing import Generator, List, Annotated, Tuple
import typer
from rich import print as pr
from rich.progress import (
    Progress,
    SpinnerColumn,
    TextColumn,
    BarColumn,
    TaskProgressColumn,
    TimeRemainingColumn,
)
import inquirer  # type: ignore
from ctags import get_ctags_path

from constants import (
    CTAGS_KINDS,
    SupportedLanguages,
    LANGUAGES_HEURISTICS,
)

FilePath = Annotated[str, "A valid filesystem path"]

app = typer.Typer()


@app.command()
def main(
    path: Annotated[
        FilePath,
        typer.Option(
            help="Root path from which Sential will start identifying modules"
        ),
    ] = ".",
    language: Annotated[
        str,
        typer.Option(
            help=f"Available languages: {', '.join([l.value for l in SupportedLanguages])}"
        ),
    ] = "",
):
    """Main entry point"""
    # Validate path is directory
    if not os.path.isdir(path):
        pr(
            f"[red]Error:[/red] Not a valid path or not a directory: [green]'{path}'[/green]"
        )
        raise typer.Exit()

    # Validate path is git repository
    try:
        subprocess.run(
            ["git", "rev-parse", "--is-inside-work-tree"],
            cwd=path,
            text=True,
            check=True,
        )
    except subprocess.CalledProcessError as e:
        pr(f"[red]Error:[/red] Not a git repository: [green]'{path}'[/green]")
        raise typer.Exit() from e

    # Validate language selection
    if not language:
        # If language not passed as arg, show options
        language = make_language_selection()
    # Validate user-entered language is supported
    elif language.lower() not in (l.value.lower() for l in SupportedLanguages):
        pr(
            f"[red]Error:[/red] Selected language not supported ([green]'{language}'[/green]),\n run [italic]sential --help[/italic] to see a list of supported languages."
        )
        raise typer.Exit()

    pr(f"\n[green]Language selected: {language}...[/green]\n")
    pr(f"[green]Scanning: {path}...[/green]\n")

    scopes = select_scope(path, SupportedLanguages(language))
    inventory_file, file_count = get_final_inventory_file(
        path, scopes, SupportedLanguages(language)
    )
    tags_map = generate_tags_jsonl(path, inventory_file, file_count)
    print(tags_map)


def get_focused_inventory(
    base_path: FilePath, language: SupportedLanguages
) -> Generator[FilePath, None, None]:
    """
    Consumes the git stream and applies the "Language Sieve" on the fly.
    """
    # 1. Get the stream (Lazy)
    raw_stream = stream_git_inventory(base_path)

    manifests_list = LANGUAGES_HEURISTICS[language]["manifests"]

    for file_path in raw_stream:
        file_name = os.path.basename(file_path)
        rel_path = os.path.dirname(file_path)

        if file_name in manifests_list:
            yield rel_path


def stream_git_inventory(base_path: FilePath) -> Generator[FilePath, None, None]:
    """
    Yields files from git index one by one.
    Zero memory overhead, even for 10 million files.
    """
    with subprocess.Popen(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
        cwd=base_path,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        bufsize=1,
    ) as process:
        if process.stdout:
            for p in process.stdout:
                yield p.strip()

        process.wait()


def select_scope(path: FilePath, language: SupportedLanguages) -> List[FilePath]:

    candidates = list(
        frozenset(p for p in get_focused_inventory(path, SupportedLanguages(language)))
    )
    candidates.sort()

    if not candidates:
        pr(
            f"[bold red]Couldn't find any[/bold red] [italic green]{language.value}[/italic green] [bold red]modules in path:[/bold red] [italic green]{path}[/italic green]"
        )
        raise typer.Exit()

    if len(candidates) == 1:
        return [candidates[0]]

    pr(
        "[bold green]Sential found multiple modules. Which ones should we focus on?[/bold green]"
    )
    choices = ["Select All"] + [f"{i+1}. {p}" for i, p in enumerate(candidates)]
    questions = [
        inquirer.Checkbox(
            "Modules",
            message="Make your selection with [SPACEBAR], then hit [ENTER] to submit",
            choices=choices,
        ),
    ]
    answers = inquirer.prompt(questions)

    if "Select All" in answers["Modules"]:
        return candidates

    selected_indices = [
        int(x.split(".")[0]) - 1
        for x in answers["Modules"]
        if x.split(".")[0].isdigit()
    ]

    return [candidates[i] for i in selected_indices if 0 <= i < len(candidates)]


def make_language_selection() -> SupportedLanguages:
    """
    Shows the user a list of supported programming languages
    from which they can select a single option
    """
    pr(
        "\n[bold green]Select the programming language for which to generate the bridge.[/bold green]"
    )
    questions = [
        inquirer.List(
            "language",
            message="Hit [ENTER] to make your selection",
            choices=[l.value for l in SupportedLanguages],
        ),
    ]

    answers = inquirer.prompt(questions)
    return SupportedLanguages(answers["language"])


def get_final_inventory_file(
    base_path: FilePath, scopes: List[FilePath], language: SupportedLanguages
) -> Tuple[FilePath, int]:
    """
    1. Asks Git for files ONLY in the selected scopes.
    2. Filters them by the language's allowed extensions.
    """
    pr("\n[bold cyan]🔍 Sifting through your codebase...[/bold cyan]")

    # Get the allowed extensions (e.g., {'.js', '.ts'})
    allowed_extensions = LANGUAGES_HEURISTICS[language]["extensions"]

    # Construct the command: git ls-files ... -- path1 path2
    # The "--" separator tells git "everything after this is a path"
    cmd = [
        "git",
        "ls-files",
        "--cached",
        "--others",
        "--exclude-standard",
        "--",
    ] + scopes

    total_files = count_git_files(base_path, cmd)

    file_count = 0
    filtered_count = 0

    with tempfile.NamedTemporaryFile(mode="w", delete=False, encoding="utf-8") as tmp:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TimeRemainingColumn(),
        ) as progress:
            task = progress.add_task(
                "[cyan]Scanning files and applying language filter...",
                total=total_files,
            )

            # Stream the results
            with subprocess.Popen(
                cmd,
                cwd=base_path,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True,
                bufsize=1,
            ) as process:
                if process.stdout:
                    for file_path in process.stdout:
                        file_path = file_path.strip()
                        file_count += 1

                        # Advance the raw counter
                        progress.update(task, advance=1)

                        # SIEVE 2: Extension Check
                        # Check if file ends with one of our valid extensions
                        # We use endswith because extensions usually include the dot
                        if any(file_path.endswith(ext) for ext in allowed_extensions):
                            tmp.write(f"{file_path}\n")
                            filtered_count += 1
                            progress.update(
                                task,
                                description=f"[cyan]Kept {filtered_count} {language} files...",
                            )

                process.wait()

            # Final update
            progress.update(
                task,
                description=f"[green]✓ Found {filtered_count} valid files",
                completed=total_files,
            )

        return tmp.name, filtered_count


def generate_tags_jsonl(
    base_path: str, inventory_path: FilePath, total_files: int
) -> FilePath:

    output_path = os.path.join(tempfile.gettempdir(), "sential_payload.jsonl")

    pr("\n[bold magenta]🏷️  Extracting code symbols...[/bold magenta]")

    ctags = get_ctags_path()
    cmd = [
        ctags,
        "--output-format=json",
        "--sort=no",
        "--fields=+n",
        "-f",
        "-",
        "-L",
        "-",
    ]

    # We accumulate the tags for the current file only
    current_file_path = None
    current_tags: List[str] = []
    tag_count = 0
    success = False

    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TimeRemainingColumn(),
        ) as progress:

            task = progress.add_task(
                f"[magenta]Parsing symbols from {total_files} files...", total=None
            )
            with open(output_path, "w", encoding="utf-8") as out_f:
                with open(inventory_path, "r", encoding="utf-8") as in_f:
                    # Use Popen to stream the output
                    with subprocess.Popen(
                        cmd,
                        cwd=base_path,
                        stdin=in_f,  # Feed the file list via stdin
                        stdout=subprocess.PIPE,  # Catch output via pipe
                        text=True,
                        bufsize=1,
                    ) as process:

                        if process.stdout:
                            for line in process.stdout:
                                try:
                                    tag = json.loads(line)
                                    path = tag.get("path")
                                    kind = tag.get("kind")
                                    name = tag.get("name")

                                    if not path or not name or kind not in CTAGS_KINDS:
                                        continue

                                    if path != current_file_path:
                                        if current_file_path:
                                            record = {
                                                "path": current_file_path,
                                                "tags": current_tags,
                                            }
                                            out_f.write(json.dumps(record) + "\n")
                                        # Reset for new file
                                        current_file_path = path
                                        current_tags = []

                                    # Add tag to current buffer
                                    current_tags.append(f"{kind} {name}")
                                    tag_count += 1

                                    # Tick the spinner occasionally
                                    if tag_count % 100 == 0:
                                        progress.update(
                                            task,
                                            description=f"[magenta]Extracted {tag_count} symbols...",
                                        )

                                except json.JSONDecodeError:
                                    continue

                        # Write the last file's tags if any
                        if current_file_path:
                            record = {
                                "path": current_file_path,
                                "tags": current_tags,
                            }
                            out_f.write(json.dumps(record) + "\n")

            progress.update(
                task,
                description=f"[green]✓ Extracted {tag_count} symbols",
                completed=100,
                total=100,
            )
            success = True

    except KeyboardInterrupt as exc:
        pr("\n[yellow]Interrupted by user[/yellow]")
        raise typer.Exit() from exc
    except Exception as e:
        pr(f"[bold red]Error: {e}[/bold red]")
        raise typer.Exit()

    finally:
        # Always clean up inventory file
        if os.path.exists(inventory_path):
            try:
                os.remove(inventory_path)
            except OSError:
                pass  # Ignore errors during cleanup

        # Clean up output file if operation was interrupted or failed
        if not success and os.path.exists(output_path):
            try:
                os.remove(output_path)
            except OSError:
                pass  # Ignore errors during cleanup

    return output_path


def count_git_files(base_path: str, cmd: List[str]) -> int:
    """
    Counts lines in the output stream without loading the file into memory.
    Memory Usage: Constant (Zero).
    """
    count = 0
    # Use Popen to open a pipe, not a buffer
    with subprocess.Popen(
        cmd,
        cwd=base_path,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        bufsize=1,  # Line buffered
    ) as process:

        # Iterate over the stream directly
        if process.stdout:
            for _ in process.stdout:
                count += 1

    return count


if __name__ == "__main__":
    app()
