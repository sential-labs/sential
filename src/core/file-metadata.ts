import {
  CATEGORY_SCORES,
  LANGUAGES_HEURISTICS,
  UNIVERSAL_CONTEXT_FILES,
} from "../constants.js";
import type { SupportedLanguage } from "../types.js";
import { FileCategory } from "./types.js";
import path from "node:path";

export class FileMetadata {
  public readonly nameLower: string;
  public readonly suffixLower: string;
  public readonly stemLower: string;
  public readonly depth: number;
  public readonly fileParentsLower: string[];
  public readonly score: number;
  public readonly category: FileCategory;

  constructor(
    public readonly filePath: string,
    public readonly language: SupportedLanguage,
  ) {
    const parsed = path.parse(filePath);

    this.nameLower = parsed.base.toLowerCase();
    this.stemLower = parsed.name.toLowerCase();
    this.suffixLower = parsed.ext.toLowerCase();

    this.fileParentsLower = parsed.dir
      .toLowerCase()
      .split(path.sep)
      .filter(Boolean);
    this.depth = this.fileParentsLower.length;

    const { category, score } = this.calculateSignificance();
    this.category = category;
    this.score = score;
  }

  private calculateSignificance() {
    const heuristics = LANGUAGES_HEURISTICS[this.language];
    const manifests = heuristics["manifests"];
    const signals = heuristics["signals"];
    const extensions = heuristics["extensions"];
    const ignoreDirs = heuristics["ignore_dirs"];

    let category: FileCategory = FileCategory.UNKNOWN;
    let score = 0;

    if (
      UNIVERSAL_CONTEXT_FILES.includes(this.nameLower) ||
      this.nameLower.startsWith("readme") ||
      this.suffixLower == ".md"
    ) {
      category = FileCategory.CONTEXT;
    } else if (
      manifests.includes(this.nameLower) ||
      manifests.includes(this.suffixLower)
    ) {
      category = FileCategory.MANIFEST;
    } else if (
      signals.includes(this.stemLower) &&
      extensions.includes(this.suffixLower)
    ) {
      category = FileCategory.SIGNAL;
    } else if (extensions.includes(this.suffixLower)) {
      category = FileCategory.SOURCE;
    }

    score = CATEGORY_SCORES[category]!;
    if (this.depth > 1) {
      score -= (this.depth - 1) * 5;
    }

    if (ignoreDirs.some((dir) => this.fileParentsLower.includes(dir))) {
      score -= 100;
    }

    return { category, score };
  }
}
