import { $ } from "bun";
import { SentialError } from "../errors.js";

export class GitClient {
  public readonly cwd: string;
  public readonly projectRoot: string;

  private constructor(cwd: string, projectRoot: string) {
    this.cwd = cwd;
    this.projectRoot = projectRoot;
  }

  public static async create(): Promise<GitClient> {
    const cwd = process.cwd();
    const projectRoot = await GitClient.findProjectRoot(cwd);
    return new GitClient(cwd, projectRoot);
  }

  private static async findProjectRoot(cwd: string): Promise<string> {
    try {
      const root = await $`git rev-parse --show-toplevel`
        .cwd(cwd)
        .quiet()
        .text();
      return root.trim();
    } catch (error) {
      throw new SentialError("Sential must be run inside a git repository.");
    }
  }

  public async countFiles(): Promise<number> {
    const files =
      $`git ls-files --cached --others --exclude-standard ${this.cwd}`
        .cwd(this.cwd)
        .quiet()
        .lines();

    let count = 0;

    for await (const _ of files) {
      count++;
    }

    return count;
  }

  public async getFilePaths(): Promise<string[]> {
    const fp = [];

    const files =
      $`git ls-files --cached --others --exclude-standard ${this.cwd}`
        .cwd(this.cwd)
        .quiet()
        .lines();

    for await (const f of files) {
      fp.push(f.trim());
    }

    return fp;
  }
}
