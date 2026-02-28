import { Tiktoken } from "js-tiktoken/lite";
import o200k_base from "js-tiktoken/ranks/o200k_base";
import { FileCategory } from "./types";

const BUDGET_CONFIG = {
  maxTotal: 200_000,
  ratios: {
    [FileCategory.CONTEXT]: 0.1,
    [FileCategory.MANIFEST]: 0.05,
    [FileCategory.SIGNAL]: 0.05,
    [FileCategory.SOURCE]: 0.4,
  },
} as const;
type CategoryWithRatio = keyof typeof BUDGET_CONFIG.ratios;
type AllocationStrategy = (category: FileCategory) => number;

const encoder = new Tiktoken(o200k_base);

function hasRatio(category: FileCategory): category is CategoryWithRatio {
  return category in BUDGET_CONFIG.ratios;
}

export class TokenBudgetManager {
  private pool = 0;

  private constructor(
    private encoder: Tiktoken,
    private getAllocation: AllocationStrategy,
  ) {}

  public static createCategorized(): TokenBudgetManager {
    return new TokenBudgetManager(encoder, (cat: FileCategory) => {
      if (hasRatio(cat)) return BUDGET_CONFIG.ratios[cat];
      return 0;
    });
  }

  public static createFlat(ratio: number = 0.6): TokenBudgetManager {
    return new TokenBudgetManager(encoder, () => ratio);
  }

  public startCategory(category: FileCategory) {
    const ratio = this.getAllocation(category);
    this.pool += Math.floor(ratio * BUDGET_CONFIG.maxTotal);
  }

  public trySpend(text: string): boolean {
    const cost = this.encoder.encode(text).length;

    if (this.pool >= cost) {
      this.pool -= cost;
      return true;
    }
    return false;
  }
}
