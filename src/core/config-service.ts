import envPaths from "env-paths";
import path from "node:path";
import fs from "node:fs/promises";
import { SentialError } from "../errors.js";
import type { ConfigData } from "./types.js";

const paths = envPaths("sential", { suffix: "" });

export class ConfigService {
  private constructor(
    private readonly configPath: string,
    private readonly configDir: string,
    private data: ConfigData | null,
  ) {}

  public static async create(): Promise<ConfigService> {
    const configPath = path.join(paths.config, "settings.json");
    const configDir = paths.config;
    let data: ConfigData | null = null;

    if (await Bun.file(configPath).exists()) {
      data = await ConfigService.load(configPath);
    }

    return new ConfigService(configPath, configDir, data);
  }

  private static async load(configPath: string): Promise<ConfigData> {
    try {
      const raw = await Bun.file(configPath).text();
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

  public async save(configData: ConfigData): Promise<void> {
    try {
      this.data = configData;
      await fs.mkdir(this.configDir, { recursive: true });
      await Bun.write(this.configPath, JSON.stringify(this.data, null, 2));
    } catch (err: any) {
      throw new SentialError(
        "Failed to save your configuration.",
        `Make sure Sential has write access to ${this.configDir}.\nError: ${err.code}`,
      );
    }
  }
}
