import { ProviderError } from "../errors";
import { LLMProvider } from "./base";
import type { LLMRequest, LLMResponse } from "./types";

export class GoogleProvider extends LLMProvider {
  get name(): string {
    return "google";
  }

  async generate(request: LLMRequest): Promise<LLMResponse> {
    try {
      const { ApiError, GoogleGenAI } = await import("@google/genai");
      const client = new GoogleGenAI({ apiKey: this.apiKey });

      const message = await client.models.generateContent({
        model: this.model,
        contents: request.prompt,
        config: {
          maxOutputTokens: request.maxTokens ?? 4096,
          temperature: request.temperature ?? 0.3,
          ...(request.systemPrompt
            ? { systemInstruction: request.systemPrompt }
            : {}),
        },
      });

      const content = message.text;
      if (!content) {
        throw new ProviderError("No response from Gemini");
      }

      return {
        content,
        usage: message.usageMetadata
          ? {
              inputTokens: message.usageMetadata.promptTokenCount ?? 0,
              outputTokens: message.usageMetadata.candidatesTokenCount ?? 0,
            }
          : undefined,
      };
    } catch (err) {
      if (err instanceof ProviderError) throw err;
      throw new ProviderError("Gemini API error", (err as Error).message);
    }
  }
}
