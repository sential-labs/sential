import { Cli } from "clerc";
import { SentialError } from "./errors.js";
import chalk from "chalk";
import { init } from "./generator/index.js";

Cli()
  .name("sential")
  .version("0.2.0")
  .scriptName("sential")
  .command("generate", "Generate artifact for current repository", {
    flags: {
      configure: {
        type: Boolean,
        short: "c",
        description:
          "Edit model and API key configuration (shows current values for editing).",
      },
    },
  })
  .on("generate", async (ctx) => {
    await init();
  })
  .errorHandler((error: any) => {
    if (error instanceof SentialError) {
      console.error(`${chalk.red.bold("Error:")} ${error.message}`);
      if (error.internalDetails) {
        console.error(chalk.dim(`Details: ${error.internalDetails}`));
      }
      process.exit(1);
    }
  })
  .parse();
