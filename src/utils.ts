import fs from "fs";
import { SentialError } from "./errors.js";

function getPathStats(path: string): fs.Stats | null {
  try {
    return fs.statSync(path);
  } catch (err: any) {
    if (err.code == "ENOENT") {
      return null;
    }
    if (err.code == "EACCES") {
      throw new SentialError(
        "Permission denied while accessing path",
        `Path: ${path}`,
      );
    }

    throw new SentialError("Filesystem error", `${err.message}`);
  }
}

export function fileExists(path: string): boolean {
  const stats = getPathStats(path);
  return stats ? stats.isFile() : false;
}

export function dirExists(path: string): boolean {
  const stats = getPathStats(path);
  return stats ? stats.isDirectory() : false;
}
