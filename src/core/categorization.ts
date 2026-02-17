import { log, progress } from "@clack/prompts";
import type { SupportedLanguage } from "../types.js";
import { FileMetadata } from "./file-metadata.js";
import { FileCategory } from "./types.js";
import chalk from "chalk";

export function categorizeFiles(
  filePaths: Array<string>,
  totalFiles: number,
  language: SupportedLanguage,
): Partial<Record<FileCategory, Array<FileMetadata>>> {
  const filesByCategory: Partial<Record<FileCategory, FileMetadata[]>> = {
    [FileCategory.CONTEXT]: [],
    [FileCategory.MANIFEST]: [],
    [FileCategory.SIGNAL]: [],
    [FileCategory.SOURCE]: [],
  };

  log.info(chalk.magenta.bold("🔍 Sifting through your codebase..."));

  const prog = progress({
    style: "heavy",
    max: totalFiles,
  });

  let itemsProcessed = 0;
  const advanceIncrement = Math.max(1, Math.trunc(totalFiles * 0.1));

  prog.start("Finding interesting files...");

  for (const fp of filePaths) {
    itemsProcessed++;
    if (itemsProcessed % advanceIncrement == 0) {
      prog.advance(advanceIncrement);
    }

    const fileMetadata = new FileMetadata(fp, language);
    if (fileMetadata.category == FileCategory.UNKNOWN) {
      continue;
    }

    filesByCategory[fileMetadata.category]?.push(fileMetadata);
  }

  const keptFilesCount = Object.entries(filesByCategory).flatMap(
    ([_, v]) => v,
  ).length;

  prog.stop(`Found ${keptFilesCount} relevant files.`);

  return filesByCategory;
}
