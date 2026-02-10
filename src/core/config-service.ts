import envPaths from "env-paths";
import path from "node:path";
import fs from "fs";
import { fileExists } from "../utils.js";
import { SentialError } from "../errors.js";
import type { ConfigData } from "./types.js";

const paths = envPaths("sential", { suffix: "" });

export class ConfigService {
  private readonly configPath = path.join(paths.config, "settings.json");
  private readonly configDir = paths.config;
  private data: ConfigData | null = null;

  constructor() {
    if (fileExists(this.configPath)) {
      this.data = this.load();
    }
  }

  private load(): ConfigData {
    try {
      const raw = fs.readFileSync(this.configPath, "utf-8");
      return JSON.parse(raw);
    } catch (err: any) {
      throw new SentialError("Config corrupted", `${err.message}`);
    }
  }

  get isInitialized(): boolean {
    return this.data !== null;
  }

  get provider(): string {
    if (!this.data) throw new Error("Config not loaded");
    return this.data.provider;
  }

  get model(): string {
    if (!this.data) throw new Error("Config not loaded");
    return this.data.model;
  }

  get apiKey(): string {
    if (!this.data) throw new Error("Config not loaded");
    return this.data.apiKey;
  }

  public save(configData: ConfigData): void {
    try {
      this.data = configData;
      fs.mkdirSync(this.configDir, { recursive: true });
      fs.writeFileSync(
        this.configPath,
        JSON.stringify(this.data, null, 2),
        "utf-8",
      );
    } catch (err: any) {
      throw new SentialError(
        "Failed to save your configuration.",
        `Make sure Sential has write access to ${this.configDir}.\nError: ${err.code}`,
      );
    }
  }
}
