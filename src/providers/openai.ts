import { ProviderError } from "../errors.js";
import { LLMProvider } from "./base.js";
import type { LLMRequest, LLMResponse } from "./types.js";

export class OpenAIProvider extends LLMProvider {
  get name(): string {
    return "openai";
  }

  async generate(request: LLMRequest): Promise<LLMResponse> {
    try {
      const { default: OpenAI } = await import("openai");
      const client = new OpenAI({ apiKey: this.apiKey });

      const messages: Array<{ role: "system" | "user"; content: string }> = [];
      if (request.systemPrompt) {
        messages.push({ role: "system", content: request.systemPrompt });
      }
      messages.push({ role: "user", content: request.prompt });

      const response = await client.chat.completions.create({
        model: this.model,
        max_tokens: request.maxTokens ?? 4096,
        temperature: request.temperature ?? 0.3,
        messages,
      });

      const content = response.choices[0]?.message?.content;
      if (!content) {
        throw new ProviderError("No response from OpenAI");
      }

      return {
        content,
        usage: response.usage
          ? {
              inputTokens: response.usage.prompt_tokens,
              outputTokens: response.usage.completion_tokens ?? 0,
            }
          : undefined,
      };
    } catch (err) {
      if (err instanceof ProviderError) throw err;
      throw new ProviderError("OpenAI API error", (err as Error).message);
    }
  }
}
