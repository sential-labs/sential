import * as clack from "@clack/prompts";
import type { ConfigData } from "../core/types.js";
import { SentialError } from "../errors.js";
import { SupportedLanguage } from "../types.js";
import { Provider } from "../providers/types.js";

export async function makeModelSelection(): Promise<ConfigData> {
  clack.note(
    "You need to select your LLM provider and enter your api key",
    "Let's set you up!",
  );
  const provider = await clack.select({
    message: "Choose LLM provider",
    options: Object.entries(Provider).map(([key, value]) => ({
      value: key,
      label: value,
    })),
  });

  if (clack.isCancel(provider)) {
    clack.cancel("Operation cancelled.");
    process.exit(0);
  }

  let model = await clack.text({
    message: "Enter model name",
    validate: (value) => {
      if (!value || !value.trim()) return "Model name cannot be empty";
      return undefined;
    },
  });

  if (clack.isCancel(model)) {
    clack.cancel("Operation cancelled.");
    process.exit(0);
  }

  let apiKey = await clack.text({
    message: "Enter API key",
    validate: (value) => {
      if (!value || !value.trim()) return "API key cannot be empty";
      return undefined;
    },
  });

  if (clack.isCancel(apiKey)) {
    clack.cancel("Operation cancelled.");
    process.exit(0);
  }

  if (typeof model == "string" && typeof apiKey == "string") {
    return {
      provider: Provider[provider as keyof typeof Provider],
      model: model.trim(),
      apiKey: apiKey.trim(),
    } as ConfigData;
  }

  throw new SentialError("Unexpected error occured while saving config.");
}

export async function makeLanguageSelection(): Promise<SupportedLanguage> {
  const language = await clack.select({
    message: "Choose a programming language",
    options: Object.entries(SupportedLanguage).map(([key, value]) => ({
      value: key,
      label: value,
    })),
  });

  if (clack.isCancel(language)) {
    clack.cancel("Operation cancelled.");
    process.exit(0);
  }

  if (typeof language == "string") {
    return SupportedLanguage[language as keyof typeof SupportedLanguage];
  }

  throw new SentialError(
    "Unexpected error occured while making language selection.",
  );
}
