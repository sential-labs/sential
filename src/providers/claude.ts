import { ProviderError } from "../errors.js";
import { LLMProvider } from "./base.js";
import type { LLMRequest, LLMResponse } from "./types.js";

export class ClaudeProvider extends LLMProvider {
  get name(): string {
    return "claude";
  }

  async generate(request: LLMRequest): Promise<LLMResponse> {
    try {
      const { default: Anthropic } = await import("@anthropic-ai/sdk");
      const client = new Anthropic({ apiKey: this.apiKey });

      const message = await client.messages.create({
        model: this.model,
        max_tokens: request.maxTokens ?? 4096,
        temperature: request.temperature ?? 0.3,
        ...(request.systemPrompt ? { system: request.systemPrompt } : {}),
        messages: [{ role: "user", content: request.prompt }],
      });

      const textBlock = message.content.find((b) => b.type == "text");
      if (!textBlock || textBlock.type != "text") {
        throw new ProviderError("No text response from Claude");
      }

      return {
        content: textBlock.text,
        usage: {
          inputTokens: message.usage.input_tokens,
          outputTokens: message.usage.output_tokens,
        },
      };
    } catch (err) {
      if (err instanceof ProviderError) throw err;
      throw new ProviderError("Claude API error:", (err as Error).message);
    }
  }
}
