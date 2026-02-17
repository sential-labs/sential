/**
 * Application-wide constants and configuration mappings.
 *
 * Defines core heuristics and configuration data used throughout the Sential CLI:
 * language-specific manifest/extension definitions, ctags symbol kind filters,
 * and universal context file patterns.
 */

import { FileCategory } from "./core/types.js";
import { SupportedLanguage } from "./types.js";

/** Language-specific heuristics for module discovery and file filtering. */
export interface LanguagesHeuristics {
  readonly manifests: readonly string[];
  readonly extensions: readonly string[];
  readonly signals: readonly string[];
  readonly ignore_dirs: readonly string[];
}

/** Language → heuristics mapping for discovery and ctags filtering. */
export const LANGUAGES_HEURISTICS: Record<
  SupportedLanguage,
  LanguagesHeuristics
> = {
  [SupportedLanguage.PY]: {
    manifests: [
      "requirements.txt",
      "pyproject.toml",
      "setup.py",
      "pipfile",
      "tox.ini",
    ],
    extensions: [".py", ".pyi"],
    signals: [
      "__init__",
      "__main__",
      "main",
      "app",
      "wsgi",
      "asgi",
      "manage",
      "run",
      "application",
      "server",
    ],
    ignore_dirs: ["tests", "test", "mocks", "benchmarks", "scripts", "htmlcov"],
  },
  [SupportedLanguage.JS]: {
    manifests: [
      "package.json",
      "deno.json",
      "yarn.lock",
      "pnpm-lock.yaml",
      "next.config.js",
      "vite.config.js",
      "tsconfig.json",
    ],
    extensions: [
      ".js",
      ".jsx",
      ".ts",
      ".tsx",
      ".mjs",
      ".cjs",
      ".vue",
      ".svelte",
      ".astro",
    ],
    signals: ["index", "main", "app", "server", "entry", "bootstrap", "start"],
    ignore_dirs: ["tests", "__tests__", "mocks", "e2e", "cypress"],
  },
  [SupportedLanguage.JAVA]: {
    manifests: [
      "pom.xml",
      "build.gradle",
      "build.gradle.kts",
      "settings.gradle",
      "mvnw",
      "gradlew",
    ],
    extensions: [".java", ".kt", ".scala", ".groovy"],
    signals: ["main", "application", "app"],
    ignore_dirs: ["test", "tests", "mocks", "samples", "it"],
  },
  [SupportedLanguage.CS]: {
    manifests: [
      ".csproj",
      ".sln",
      ".fsproj",
      ".vbproj",
      "global.json",
      "nuget.config",
    ],
    extensions: [".cs", ".fs", ".vb", ".cshtml", ".razor"],
    signals: ["program", "startup", "app", "main", "module1"],
    ignore_dirs: ["tests", "test", "mocks", "spec", "samples", "TestResults"],
  },
  [SupportedLanguage.GO]: {
    manifests: ["go.mod", "go.sum", "go.work", "main.go"],
    extensions: [".go"],
    signals: ["main", "server", "app", "cmd", "doc"],
    ignore_dirs: ["tests", "test", "vendor", "testdata", "mocks", "bench"],
  },
  [SupportedLanguage.CPP]: {
    manifests: [
      "cmakelists.txt",
      "makefile",
      "configure.ac",
      "meson.build",
      "conanfile.txt",
      "vcpkg.json",
      ".gitmodules",
    ],
    extensions: [
      ".c",
      ".cpp",
      ".h",
      ".hpp",
      ".cc",
      ".hh",
      ".cxx",
      ".hxx",
      ".m",
      ".mm",
    ],
    signals: ["main", "app", "application"],
    ignore_dirs: [
      "tests",
      "test",
      "mocks",
      "samples",
      "third_party",
      "vendor",
      "external",
    ],
  },
} as const;

export const CATEGORY_SCORES: Partial<Record<FileCategory, number>> = {
  [FileCategory.CONTEXT]: 1000,
  [FileCategory.MANIFEST]: 80,
  [FileCategory.SIGNAL]: 60,
  [FileCategory.SOURCE]: 50,
  [FileCategory.UNKNOWN]: 0,
} as const;

/** ctags symbol kinds extracted for context (classes, functions, structs, etc.). */
export const CTAGS_KINDS: readonly string[] = [
  "class",
  "method",
  "function",
  "struct",
  "enum",
  "union",
  "interface",
  "typedef",
  "type",
  "namespace",
  "module",
  "package",
];

/** High-value context filenames (case-insensitive) always included in context. */
export const UNIVERSAL_CONTEXT_FILES: readonly string[] = [
  "readme.md",
  "readme.txt",
  "architecture.md",
  "contributing.md",
  "design.md",
  "claude.md",
  ".cursorrules",
  ".windsurfrules",
  ".env.example",
  ".env.template",
  "docker-compose.yml",
  "dockerfile",
  "makefile",
  "justfile",
  "rakefile",
  "procfile",
];
