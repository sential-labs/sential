import { execSync, spawn } from "node:child_process";
import { createInterface } from "node:readline";
import { SentialError } from "../errors.js";

export class GitClient {
  public readonly cwd: string;
  public readonly projectRoot: string;

  constructor() {
    this.cwd = process.cwd();
    this.projectRoot = this.findProjectRoot();
  }

  public findProjectRoot(): string {
    try {
      const root = execSync("git rev-parse --show-toplevel", {
        cwd: this.cwd,
        encoding: "utf-8",
        // stdio takes [subprocess.stdin, subprocess.stdout, subprocess.stderr]
        // we only need stdout
        stdio: ["ignore", "pipe", "ignore"],
      });
      return root.trim();
    } catch (error) {
      throw new SentialError("Sential must be run inside a git repository.");
    }
  }

  public async countFiles(): Promise<number> {
    const child = spawn(
      "git",
      ["ls-files", "--cached", "--others", "--exclude-standard", this.cwd],
      {
        cwd: this.cwd,
      },
    );

    const rl = createInterface({ input: child.stdout });

    let count = 0;

    for await (const _ of rl) {
      count++;
    }

    return count;
  }

  public async getFilePaths(): Promise<Array<string>> {
    const fp = [];

    const child = spawn(
      "git",
      ["ls-files", "--cached", "--others", "--exclude-standard", this.cwd],
      {
        cwd: this.cwd,
      },
    );

    const rl = createInterface({ input: child.stdout });

    for await (const l of rl) {
      fp.push(l.trim());
    }

    return fp;
  }
}
