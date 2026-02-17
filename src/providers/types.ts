export interface LLMRequest {
  prompt: string;
  systemPrompt?: string;
  maxTokens?: number;
  temperature?: number;
}

export interface LLMResponse {
  content: string;
  usage?: {
    inputTokens: number;
    outputTokens: number;
  };
}

export enum Provider {
  CLAUDE = "claude",
  OPENAI = "openai",
  GOOGLE = "google",
}
