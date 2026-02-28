import { $ } from "bun";
import path from "node:path";
import type { FileMetadata } from "./file-metadata";
import { TokenBudgetManager } from "./tokens";
import { FileCategory, type Ctag, type ProcessedFile } from "./types";
import { getCtagsPath } from "../adapters/ctags";
import { SentialError } from "../errors";
import { CTAGS_KINDS } from "../constants";
import { taskLog } from "@clack/prompts";
import chalk from "chalk";

export async function processFiles(
  root: string,
  filesByCategory: Partial<Record<FileCategory, FileMetadata[]>>,
): Promise<Partial<Record<FileCategory, ProcessedFile[]>>> {
  const processedFiles: Partial<Record<FileCategory, ProcessedFile[]>> = {
    [FileCategory.CONTEXT]: [],
    [FileCategory.MANIFEST]: [],
    [FileCategory.SIGNAL]: [],
    [FileCategory.SOURCE]: [],
  };

  const categories = Object.keys(processedFiles) as FileCategory[];
  const tokenBudget = TokenBudgetManager.createCategorized();

  for (const cat of categories) {
    const filesInCategory = filesByCategory[cat];

    if (!filesInCategory || filesInCategory.length == 0) {
      continue;
    }

    // higher scores first, if scores equal, shallowest depth first
    filesInCategory.sort((a, b) => b.score - a.score || a.depth - b.depth);

    if (cat == FileCategory.SOURCE) {
      processedFiles[cat] = await extractCtags(
        root,
        cat,
        filesInCategory,
        tokenBudget,
      );
    } else {
      processedFiles[cat] = await processReadableFilesForCategory(
        root,
        cat,
        filesInCategory,
        tokenBudget,
      );
    }
  }

  return processedFiles;
}

async function processReadableFilesForCategory(
  root: string,
  category: FileCategory,
  filesInCategory: FileMetadata[],
  tokenBudget: TokenBudgetManager,
  chapterName?: string,
): Promise<ProcessedFile[]> {
  if (category == FileCategory.SOURCE || category == FileCategory.UNKNOWN) {
    throw new Error(
      "Tried reading source or unknown files which is not permitted.",
    );
  }

  const categoryToText = {
    [FileCategory.CONTEXT]: {
      title: "📖 Establishing project context...",
      description: "context files",
    },
    [FileCategory.MANIFEST]: {
      title: "📦 Analyzing manifest & dependency files...",
      description: "manifest files",
    },
    [FileCategory.SIGNAL]: {
      title: "🎯 Identifying high-signal entry points...",
      description: "high-signal files",
    },
    [FileCategory.CHAPTER_FILE]: {
      title: `📖 Reading files for chapter ${chapterName}`,
      description: "files for chapter ${chapterName}",
    },
  };

  const processedFiles: ProcessedFile[] = [];
  let processedFilesCount = 0;

  const log = taskLog({
    title: chalk.magenta.bold(categoryToText[category].title),
    limit: 2,
    retainLog: false,
  });

  log.message(`Reading ${categoryToText[category].description}...`);

  tokenBudget.startCategory(category);

  for (const f of filesInCategory) {
    const fullPath = path.join(root, f.filePath);
    try {
      const content = await Bun.file(fullPath).text();
      if (tokenBudget.trySpend(content)) {
        processedFiles.push({
          path: f.filePath,
          type: category,
          content,
        });
        processedFilesCount += 1;
      } else {
        break;
      }
    } catch (err) {
      continue;
    }
  }

  log.success(
    `Read ${processedFilesCount} ${categoryToText[category].description}.`,
  );

  return processedFiles;
}

async function extractCtags(
  root: string,
  category: FileCategory,
  filesInCategory: FileMetadata[],
  tokenBudget: TokenBudgetManager,
): Promise<ProcessedFile[]> {
  if (category != FileCategory.SOURCE) {
    throw new Error("Ctags must only be run on source files.");
  }

  const files: ProcessedFile[] = [];
  const ctagsPath = await getCtagsPath();

  let startIdx = 0;
  let filesProcessed = 0;
  let budgetExhausted = false;
  let listFullyProcessed = false;

  tokenBudget.startCategory(category);

  const log = taskLog({
    title: chalk.magenta.bold("👀  Looking into source files..."),
    limit: 2,
    retainLog: false,
  });

  log.message("Extracting code symbols from source files...");

  while (true) {
    const { processedFiles, currentIdx } = await runCtags(
      root,
      category,
      filesInCategory,
      ctagsPath,
      startIdx,
    );

    startIdx = currentIdx;

    if (processedFiles.length == 0) break;

    if (startIdx >= filesInCategory.length) {
      listFullyProcessed = true;
    }

    for (const file of processedFiles) {
      if (tokenBudget.trySpend(file.content)) {
        files.push(file);
        filesProcessed += 1;
      } else {
        budgetExhausted = true;
        break;
      }
    }

    if (budgetExhausted || listFullyProcessed) break;
  }

  log.success(`Extracted code symbols for ${filesProcessed} files.`);

  return files;
}

async function runCtags(
  root: string,
  category: FileCategory,
  filesInCategory: FileMetadata[],
  ctagsPath: string,
  start: number = 0,
  limit: number = 100,
) {
  if (category != FileCategory.SOURCE) {
    throw new Error("Ctags must only be run on source files.");
  }

  const stop = start + limit;
  const processedFiles: ProcessedFile[] = [];
  let currentIdx = start;

  const fullFilePaths = filesInCategory
    .slice(start, stop)
    .map((f) => path.join(root, f.filePath));

  let currentFilePath = null;
  let currentFileTags: string[] = [];

  try {
    const args = [
      "--output-format=json",
      "--sort=no",
      "--fields=+n",
      "-f",
      "-",
    ];
    const proc = $`${ctagsPath} ${args} ${fullFilePaths}`.nothrow().quiet();
    for await (const line of proc.lines()) {
      if (!line.trim()) continue;

      try {
        const tag = JSON.parse(line);
        const ctag = parseTagLine(tag);

        if (!ctag) continue;

        if (ctag?.path != currentFilePath) {
          if (currentFilePath) {
            processedFiles.push({
              path: getRelativePath(root, currentFilePath),
              type: category,
              content: currentFileTags.join("\n"),
            });
          }
          currentFilePath = ctag?.path;
          currentFileTags = [];
          currentIdx += 1;
        }
        currentFileTags.push(`${ctag?.kind} ${ctag?.name}`);
      } catch (e) {
        continue;
      }
    }
  } catch (err: any) {
    if (err instanceof $.ShellError) {
      throw new SentialError(
        "Something went wrong when generating code symbols.",
        err.stderr?.toString() || "Process failed",
      );
    }
    throw err;
  }

  if (currentFilePath) {
    processedFiles.push({
      path: getRelativePath(root, currentFilePath),
      type: category,
      content: currentFileTags.join("\n"),
    });
  }

  return { processedFiles, currentIdx };
}

function getRelativePath(root: string, fullFilePath: string): string {
  return path.relative(root, fullFilePath);
}

function parseTagLine(tag: any): Ctag | null {
  const path = tag?.path;
  const kind = tag?.kind;
  const name = tag?.name;

  if (!path || !name || !CTAGS_KINDS.includes(kind)) return null;

  return { path, kind, name } as Ctag;
}
