from pathlib import Path
import inquirer  # type: ignore
from inquirer.themes import GreenPassion  # type: ignore
from rich import print as pr
import typer

# Note: You will need to import get_focused_inventory from core.discovery here
from constants import SupportedLanguage
from core.discovery import get_focused_inventory


def select_scope(path: Path, language: SupportedLanguage) -> list[str]:
    """
    Prompts the user to select which modules (scopes) to include in the scan.

    This function first identifies all potential modules using `get_focused_inventory`.
    If multiple modules are found, it presents an interactive checklist (using `inquirer`)
    allowing the user to select specific modules or "Select All".

    Args:
        path (Path): The absolute root path of the repository.
        language (SupportedLanguages): The selected programming language, used to locate modules.

    Returns:
        list[str]: A list of relative path strings representing the selected module roots.
        Returns the original candidate list immediately if "Select All" is chosen or if
        only one module is found.

    Raises:
        typer.Exit: If no modules matching the language heuristics are found in the path.
    """

    candidates = sorted(
        set(str(p) for p in get_focused_inventory(path, SupportedLanguage(language)))
    )

    if not candidates:
        pr(
            f"[bold red]Couldn't find any[/bold red] [italic green]{language}[/italic green] [bold red]modules in path:[/bold red] [italic green]{path}[/italic green]"
        )
        raise typer.Exit()

    if len(candidates) == 1:
        return [candidates[0]]

    pr(
        "[bold green]Sential found multiple modules. Which ones should we focus on?[/bold green]\n"
    )

    # This will look like:
    # [] Select All
    # [] (Root)
    # [] src
    # [] src/bin
    # And the value will be the actual path
    # e.g. (Root) -> "."
    choices = [("Select All", "ALL")] + [
        (p if p != "." else "(Root)", p) for p in candidates
    ]

    questions = [
        inquirer.Checkbox(
            "Modules",
            message="Make your selection with [SPACEBAR], then hit [ENTER] to submit",
            choices=choices,
        ),
    ]

    # This will contain just the indexes in the above choices list of tuples
    answers = inquirer.prompt(questions, theme=GreenPassion())
    if not answers:
        raise typer.Exit()

    selection = answers["Modules"]

    # Just return the candidates list
    if "ALL" in selection:
        return candidates

    return selection


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
            choices=[l for l in SupportedLanguage],
        ),
    ]

    answers = inquirer.prompt(questions, theme=GreenPassion())

    if not answers:
        raise typer.Exit()

    return SupportedLanguage(answers["language"])
