import { log, progress, taskLog } from "@clack/prompts";
import type { SupportedLanguage } from "../types.js";
import { FileMetadata } from "./file-metadata.js";
import { FileCategory } from "./types.js";
import chalk from "chalk";

export function categorizeFiles(
  filePaths: string[],
  totalFiles: number,
  language: SupportedLanguage,
): Partial<Record<FileCategory, FileMetadata[]>> {
  const filesByCategory: Partial<Record<FileCategory, FileMetadata[]>> = {
    [FileCategory.CONTEXT]: [],
    [FileCategory.MANIFEST]: [],
    [FileCategory.SIGNAL]: [],
    [FileCategory.SOURCE]: [],
  };

  const log = taskLog({
    title: chalk.magenta.bold("🔍 Sifting through your codebase..."),
    limit: 2,
    retainLog: false,
  });

  let itemsProcessed = 0;

  log.message("Finding interesting files...");

  for (const fp of filePaths) {
    itemsProcessed++;

    const fileMetadata = new FileMetadata(fp, language);
    if (fileMetadata.category == FileCategory.UNKNOWN) {
      continue;
    }

    filesByCategory[fileMetadata.category]?.push(fileMetadata);
  }

  const keptFilesCount = Object.entries(filesByCategory).flatMap(
    ([_, v]) => v,
  ).length;

  log.success(`Found ${keptFilesCount} relevant files.`);

  return filesByCategory;
}
