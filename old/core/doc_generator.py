from pathlib import Path
from rich import print as pr
from time import sleep
from core.file_io import FilesystemFileWriter
from core.llm import ask_llm, get_config_file
from core.models import CategoryProcessedFiles, FileCategory
from core.processing import process_chapter_files
from core.prompts import SyllabusResult, build_chapter_payload, build_chapter_prompt
from core.tokens import FixedTokenBudget, TiktokenCounter


DOC_TITLE = "Codebase Guide"


def process_syllabus_result(root: Path, result: SyllabusResult):
    proj_context = result.project_context

    fw = FilesystemFileWriter(root / "Overview.md")
    fw.write_file(f"# {DOC_TITLE}\n\n")

    for ch in result.chapters:
        pr(f"\n[bold magenta] Generating chapter: {ch.order}.{ch.title}")
        ch_title = ch.title
        ch_index = ch.order
        ch_files = ch.file_paths
        ch_prompt = build_chapter_prompt(proj_context, ch_title, ch_index)

        processed_files = CategoryProcessedFiles(FileCategory.CHAPTER_FILE)
        process_chapter_files(
            ch_files,
            ch_title,
            TiktokenCounter(),
            FixedTokenBudget(200_000, 0.6),
            processed_files,
        )
        prompt = build_chapter_payload(ch_prompt, processed_files.files)

        config = get_config_file()
        model = config.get("model")
        api_key = config.get("api_key")

        resp = ask_llm(model, api_key, prompt)
        fw.write_file(f"## {ch_index}. {ch_title}\n\n{resp.strip()}\n\n", "a")
        sleep(15)
