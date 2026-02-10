import { intro, outro } from "@clack/prompts";
import chalk from "chalk";
import { ConfigService } from "../core/config-service.js";
import { makeLanguageSelection, makeModelSelection } from "./helpers.js";
import { GitClient } from "../adapters/git.js";
import { categorizeFiles } from "../core/categorization.js";

export async function init(): Promise<void> {
  intro(chalk.green.bold("Welcome to sential! 👋"));

  const configService = new ConfigService();
  if (!configService.isInitialized) {
    const data = await makeModelSelection();
    configService.save(data);
  }

  const gitClient = new GitClient();
  const totalFiles = await gitClient.countFiles();
  const filePaths = await gitClient.getFilePaths();

  const language = await makeLanguageSelection();

  const categorizedFiles = categorizeFiles(filePaths, totalFiles, language);

  outro(chalk.green.bold("See you soon... 👋"));
}
