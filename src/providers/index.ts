import type { LLMProvider } from "./base.js";
import { ClaudeProvider } from "./claude.js";
import { OpenAIProvider } from "./openai.js";
import type { ConfigData } from "../core/types.js";
import { ProviderError } from "../errors.js";

export function createProvider(config: ConfigData): LLMProvider {
  const model = config.model!;

  switch (config.provider) {
    case "claude":
      return new ClaudeProvider(model, config.apiKey);
    case "openai":
      return new OpenAIProvider(model, config.apiKey);
    default:
      throw new ProviderError(`Unknown provider: ${config.provider}`);
  }
}

export type { LLMProvider } from "./base.js";
