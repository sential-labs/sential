import type { Provider } from "../providers/types.js";

export interface ConfigData {
  provider: Provider;
  model: string;
  apiKey: string;
}

export enum FileCategory {
  CONTEXT = "context_file",
  MANIFEST = "manifest_file",
  SIGNAL = "signal_file",
  SOURCE = "source_file",
  CHAPTER_FILE = "chapter_file",
  UNKNOWN = "generic_file",
}
