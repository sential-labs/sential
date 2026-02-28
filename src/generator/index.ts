import os from "node:os";
import path from "node:path";
import { intro, outro } from "@clack/prompts";
import chalk from "chalk";
import { ConfigService } from "../core/config-service.js";
import { makeLanguageSelection, makeModelSelection } from "./helpers.js";
import { GitClient } from "../adapters/git.js";
import { categorizeFiles } from "../core/categorization.js";
import { processFiles } from "../core/processing.js";

export async function init(): Promise<void> {
  intro(chalk.green.bold("Welcome to sential! 👋"));

  const configService = await ConfigService.create();
  if (!configService.isInitialized) {
    const data = await makeModelSelection();
    await configService.save(data);
  }

  const gitClient = await GitClient.create();
  const totalFiles = await gitClient.countFiles();
  const filePaths = await gitClient.getFilePaths();
  const rootPath = gitClient.projectRoot;

  const language = await makeLanguageSelection();

  const payloadFile = path.join(os.tmpdir(), `sential_payload.jsonl`);

  const categorizedFiles = categorizeFiles(filePaths, totalFiles, language);
  const processedFiles = await processFiles(rootPath, categorizedFiles);
  outro(chalk.green.bold("See you soon... 👋"));
}
