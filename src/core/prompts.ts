const SYLLABUS_GENERATION_PROMPT = `You are analyzing a codebase from a JSONL payload. The payload contains:
1. This prompt.
2. A series of documents: each line is a JSON object with "path", "type", and "content". Types include context files (README, docs), manifest files (package.json, requirements.txt, etc.), signal files (entry points), and source files (often as ctags/symbols only).
3. A final line with "type": "file_paths" and "paths": [ ... ] — the full list of every file path in the repository (relative to repo root).

Purpose of the overall effort: The output of this step will be used to generate technical documentation that acts as a map and a technical reference through the codebase for a new engineer. The final document should be as logical, well‑structured, and methodical as a staff‑level engineer explaining the codebase in person: the reader should become able to navigate the codebase, understand what is happening, and grasp design decisions and technicalities.

Your task:
- Get an overview of the application: what it does, its high-level architecture, and how it is structured.
- Write a short "project context" (see output format) that summarizes the project: what it is, its main purpose, high-level architecture, and key technologies. This will be reused at the top of every chapter prompt so each chapter is grounded in the same big picture. Keep it to 2–4 short paragraphs; be concise but informative.
- Identify the most important flows, patterns, and technical themes (e.g. auth, APIs, messaging, testing, configuration). Focus on what is particular to this project and what is central to how it works.
- Produce a syllabus: an ordered list of "chapters" (topics) that would best explain this codebase to someone new. Each chapter should be a coherent theme (e.g. "Authentication & authorization", "Event handling", "Database layer", "Testing"). Order chapters so that foundational topics come first and dependents later when sensible.
- For each chapter, select the file paths that are most relevant to that topic. Use only paths that appear exactly in the "file_paths" list from the payload. Include both files already present in the payload (e.g. README, main entry points) and other repo paths that would give the best context for that chapter when read in a fresh context window. Prefer a focused set per chapter (e.g. 5–20 paths) rather than listing everything.

Output format (strict):
Reply with a single JSON object that is easy to parse from Python. You may wrap it in a markdown code block ("""json ... """). The object must have exactly this shape:

{
  "project_context": "2–4 short paragraphs of plain text or markdown: what the project is, main purpose, high-level architecture, key technologies. No code blocks.",
  "chapters": [
    {
      "order": 1,
      "title": "Exact chapter title",
      "file_paths": ["path/from/file_paths/list", "another/path.ext", ...]
    },
    ...
  ]
}

Rules:
- "project_context" must be a non-empty string (2–4 paragraphs). It will be injected at the start of every chapter prompt; keep it concise.
- "order" must be a positive integer; chapters must be in ascending order (1, 2, 3, ...).
- "title" is a short, clear string for the chapter.
- "file_paths" must be an array of strings. Every string must be exactly one of the paths from the "file_paths" line in the payload (no new paths, no typos). Paths can be repeated across chapters if relevant.
- Output only the JSON object (optionally inside """json ... """). No other commentary before or after.`;

// -----------------------------------------------------------------------------
// Chapter documentation prompt (modular blocks, composed for each chapter)
// -----------------------------------------------------------------------------

const AUDIENCE_AND_GOAL = `Audience and goal:
- You are writing for a new engineer joining the project (software engineer or related technical role). Assume they are technical but do not assume they know this codebase.
- This document should act as a map first and a technical reference through the codebase. By the end, the reader should be able to navigate the codebase, understand what is happening, and understand design decisions and technicalities — as if a staff-level engineer had walked them through it.
- Write at the depth a staff engineer would when onboarding someone: logical, methodical, and thorough. Prefer thoroughness over brevity; do not skip important details for the sake of conciseness.`;

const CHAPTER_STYLE_GUIDE = `Markdown style (follow strictly so the final document is cohesive):
- Do not output a chapter title or H2 heading. We will prepend "## N. Chapter title" in code. Start your response directly with the first section (e.g. "### Overview").
- Use H3 for main sections (e.g. "### Overview", "### Key components", "### Design decisions").
- Use H4 for subsections when needed.
- Use fenced code blocks with a language tag (e.g. \`\`\`python, \`\`\`typescript). When referencing a file path in prose, use inline code (e.g. \`src/auth/service.py\`).
- Use bullet lists with "-". When referring to specific symbols (functions, classes, types), use inline code.`;

const CHAPTER_COVERAGE = `Coverage for this chapter:
- Structure your response with clear subsections. Aim to: (a) orient the reader on what this area does, (b) point to specific files and symbols that matter, (c) explain non-obvious design decisions or patterns that appear in the code, (d) mention how this area connects to the rest of the system where relevant.
- Base your documentation strictly on the provided file contents and the project context below. Do not invent or assume details not present. Be as specific as possible: cite files, modules, and key types or functions by name so the doc serves as a real map and reference.
- Assume the reader may not have read other chapters; make this chapter self-contained where possible, but you may refer to other areas of the codebase by name.`;

const CHAPTER_TASK_INTRO = `You are writing one chapter of a multi-chapter technical documentation for this codebase. The same project context is provided below so you share a consistent big picture with other chapters. You are given only the file content relevant to this chapter so your context is focused. Your output will be concatenated with other chapters into a single final markdown document.`;

const buildChapterPrompt = (
  project_context: string,
  chapter_index: string,
  chapter_title: string,
) => `${CHAPTER_TASK_INTRO}

---
Project context (shared across all chapters):
---
${project_context}

---
Your chapter: ${chapter_index}. ${chapter_title}
---

${AUDIENCE_AND_GOAL}

${CHAPTER_STYLE_GUIDE}

${CHAPTER_COVERAGE}

Output: Produce only the chapter body (no chapter heading—we add it). Start with your first H3 section; no preamble or meta-commentary. The following content (file contents and/or symbols) is provided for this chapter. Use it as the sole source for your documentation.
`;
