# Sential v1 — Architecture & Implementation Plan

> **Status:** Definitive reference for the full v1 implementation.
> **Last updated:** 2026-02-28

---

## 1. What Sential Is

Sential is a **codebase intelligence platform that provides personalized, progressive onboarding experiences**. It maps code architecture through static analysis and generates tailored learning guides for each engineer — meeting them where they are based on their existing knowledge and growing with them as they explore deeper.

The platform operates in two layers:

- **Structural Intelligence (shared, global):** Sential indexes repositories using tree-sitter AST parsing, builds dependency graphs, runs centrality analysis, and detects community clusters. This produces an interactive architecture map — a visual, navigable landscape of the codebase. No LLM involved, no API cost. This layer is shared across all users.
- **Personalized Learning (per-user, on-demand):** Individual engineers create a profile describing their background (languages, frameworks, experience level) and launch scoped learning sessions against any indexed repository. Sential's multi-agent LLM pipeline generates narrative guides tailored to the user's existing knowledge, focused on their chosen scope (a subsystem, a service, or the full repo). Each session builds on the last — the system remembers what was already explained and extends rather than repeats.

The product is the **web interface itself**: architecture maps, user profiles, scoped learning sessions, and chapter-based narrative content rendered in the browser. Organizations self-host Sential via Docker, pointed at their repositories.

### 1.1 Deployment Model

Sential follows the **Sourcegraph model**: a self-hosted, Docker-packaged application. An admin deploys and configures the infrastructure; individual engineers use it through the web UI. The Docker image bundles:

- Python backend (FastAPI)
- React frontend (static build served by the backend)
- SQLite database (application state, graph data, generated content)
- LanceDB vector store (per-repository embeddings)
- Tree-sitter parsers (bundled native grammars)

External dependencies the host environment must provide:

- **Redis** — job queue, caching, session state
- **Git-accessible repositories** — local paths or cloneable URLs
- **LLM API keys** — organization-provided (OpenAI, Anthropic, Google)

A `docker-compose.yml` ships with the project for one-command local setup (Sential + Redis).

### 1.2 Admin vs. User Roles


| Role                | Responsibilities                                                                                                     |
| ------------------- | -------------------------------------------------------------------------------------------------------------------- |
| **Admin**           | Deploys Sential, registers repositories, configures indexing schedule, provides LLM API keys, manages infrastructure |
| **User (Engineer)** | Creates their profile, browses architecture maps, creates learning sessions, reads and explores generated content    |


Repository indexing (structural analysis) is the admin's concern. Engineers never have to think about parsing, graphs, or infrastructure — they see architecture maps and generate personalized guides.

### 1.3 License

BSL 1.1. Free for personal use. Commercial use for teams >3 requires a license. Auto-converts to Apache 2.0 on Jan 1, 2029.

---

## 2. Technology Stack


| Layer                        | Technology                                       | Rationale                                                                                            |
| ---------------------------- | ------------------------------------------------ | ---------------------------------------------------------------------------------------------------- |
| **Language**                 | Python 3.12+                                     | Best ecosystem for AI orchestration, AST tooling, graph algorithms                                   |
| **Dependency management**    | uv                                               | Fast, modern, deterministic lockfiles, replaces pip/poetry/pipenv                                    |
| **Web framework**            | FastAPI                                          | Async, type-safe, automatic OpenAPI docs, excellent Pydantic integration                             |
| **Task queue**               | arq (Redis-backed)                               | Lightweight async job queue for Python; fits the Redis dependency naturally                          |
| **Agent orchestration**      | Pydantic AI                                      | Type-safe structured outputs, model-agnostic, dependency injection, retry on validation failure      |
| **AST parsing**              | tree-sitter (py-tree-sitter + language grammars) | Multi-language, full AST, battle-tested, used by GitHub/Neovim/Zed                                   |
| **Graph computation**        | NetworkX                                         | In-memory graph algorithms (PageRank, betweenness centrality, community detection, topological sort) |
| **Structured persistence**   | SQLite (via aiosqlite)                           | Embedded, single-file, zero-config; stores graph, pipeline state, generated content, file hashes     |
| **Vector search**            | LanceDB                                          | Embedded, serverless, on-disk vectors; semantic retrieval for contextual features                    |
| **Caching / queue backend**  | Redis                                            | Job queue backend (arq), LLM response caching, session state                                         |
| **Frontend**                 | React 19 + TypeScript + Vite                     | Modern, proven, massive ecosystem; Vite for fast builds                                              |
| **Frontend styling**         | Tailwind CSS 4                                   | Utility-first, fast iteration, no CSS architecture decisions                                         |
| **Frontend state**           | TanStack Query                                   | Server state management, caching, background refetching                                              |
| **Graph visualization**      | React Flow or D3.js                              | Interactive, pan/zoom architecture diagrams rendered from real graph data                            |
| **Diagram rendering**        | Mermaid.js                                       | Sequence diagrams, ERDs, flowcharts embedded in narrative content                                    |
| **Markdown rendering**       | react-markdown + rehype/remark plugins           | Render LLM-generated markdown with syntax highlighting, Mermaid blocks, and cross-references         |
| **Code syntax highlighting** | Shiki                                            | Accurate, VS Code-quality highlighting for all languages                                             |
| **Containerization**         | Docker (multi-stage build)                       | Single image: Python backend + static frontend assets                                                |
| **Orchestration**            | docker-compose                                   | Ships with the project for one-command local deployment                                              |


---

## 3. System Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│                          Docker Container                            │
│                                                                      │
│  ┌──────────────┐    ┌───────────────────────────────────────────┐   │
│  │ React SPA    │    │ FastAPI Backend                           │   │
│  │ (static,     │    │                                           │   │
│  │  served by   │◄──►│  ┌──────────┐  ┌──────────┐               │   │
│  │  FastAPI)    │    │  │ REST API │  │ WebSocket│               │   │
│  └──────────────┘    │  │ routes   │  │ (progress│               │   │
│                      │  └────┬─────┘  │ streams) │               │   │
│                      │       │        └────┬─────┘               │   │
│                      │       ▼             │                     │   │
│                      │  ┌──────────────────▼────────────┐        │   │
│                      │  │  Two-Layer Pipeline           │        │   │
│                      │  │                               │        │   │
│                      │  │  Layer 1: Structural Analysis │        │   │
│                      │  │  (admin-triggered, no LLM)    │        │   │
│                      │  │  ┌─────────┐  ┌──────────┐    │        │   │
│                      │  │  │Ingestion│  │  Graph   │    │        │   │
│                      │  │  │(tree-   │─►│  Builder │    │        │   │
│                      │  │  │ sitter) │  │(NetworkX)│    │        │   │
│                      │  │  └─────────┘  └────┬─────┘    │        │   │
│                      │  │              ┌─────▼──────┐   │        │   │
│                      │  │              │ Centrality │   │        │   │
│                      │  │              │ + Community│   │        │   │
│                      │  │              └────────────┘   │        │   │
│                      │  │                               │        │   │
│                      │  │  Layer 2: Narrative Generation│        │   │
│                      │  │  (user-triggered, LLM-powered)│        │   │
│                      │  │  ┌────────────────────────┐   │        │   │
│                      │  │  │  Agent Pipeline        │   │        │   │
│                      │  │  │  (Pydantic AI)         │   │        │   │
│                      │  │  │  Planner → Writer →    │   │        │   │
│                      │  │  │  Verifier → Summarizer │   │        │   │
│                      │  │  └────────────────────────┘   │        │   │
│                      │  └───────────────────────────────┘        │   │
│                      │       │              │                    │   │
│                      │       ▼              ▼                    │   │
│                      │  ┌─────────┐  ┌───────────┐               │   │
│                      │  │ SQLite  │  │ LanceDB   │               │   │
│                      │  │ (.db)   │  │ (vectors) │               │   │
│                      │  └─────────┘  └───────────┘               │   │
│                      └───────────────────────────────────────────┘   │
│                             │                                        │
│                             ▼                                        │
│                      ┌─────────────┐                                 │
│                      │    Redis    │ (external, via docker-compose)  │
│                      └─────────────┘                                 │
└──────────────────────────────────────────────────────────────────────┘
```

### 3.1 Data Flow Summary

```
                         LAYER 1: STRUCTURAL ANALYSIS
                         (admin-triggered, shared, no LLM)

Git Repository
    │
    ▼
[1] Ingestion ─── tree-sitter parses every file into ASTs
    │
    ▼
[2] Graph Construction ─── extract imports, class hierarchy, function calls → NetworkX DAG
    │
    ▼
[3] Centrality Analysis ─── PageRank + betweenness + Louvain → core 20%, community clusters
    │
    ▼
[4] Persist ─── serialize graph + centrality + communities + file metadata → SQLite
    │
    ▼
[5] Architecture Map ─── served to all users via the web UI


                         LAYER 2: NARRATIVE GENERATION
                         (user-triggered, scoped, personalized)

User creates a Learning Session (scope + profile + goal)
    │
    ▼
[6] Scope Resolution ─── extract subgraph for the selected scope (cluster, directory, or full repo)
    │
    ▼
[7] Agent Pipeline ─── Planner → Writer → Verifier → Summarizer (Pydantic AI)
    │                   (Canon Pack includes user profile for personalization)
    ▼
[8] Store Output ─── chapters (markdown), Canon Pack, ledger entries → SQLite
    │
    ▼
[9] Serve ─── FastAPI reads from SQLite → React renders personalized guides
```

---

## 4. Project Structure

```
sential/
├── docker-compose.yml              # Sential + Redis one-command setup
├── Dockerfile                      # Multi-stage: build frontend → bundle with backend
├── pyproject.toml                  # Python project config (uv)
├── uv.lock                         # Deterministic lockfile
├── alembic.ini                     # DB migration config
├── ARCHITECTURE.md                 # This document
│
├── backend/
│   ├── __init__.py
│   ├── main.py                     # FastAPI app factory, lifespan, middleware
│   ├── config.py                   # Settings via pydantic-settings (env vars)
│   ├── database.py                 # SQLite connection management (aiosqlite)
│   │
│   ├── models/                     # SQLAlchemy ORM models (SQLite tables)
│   │   ├── __init__.py
│   │   ├── repository.py           # Repository registration and metadata
│   │   ├── graph.py                # Nodes and edges tables (serialized graph)
│   │   ├── analysis.py             # Centrality scores, community assignments
│   │   ├── pipeline.py             # Pipeline run state, phase completion
│   │   ├── content.py              # Generated chapters, Canon Pack, diagrams
│   │   ├── user_profile.py         # User profiles (languages, frameworks, experience)
│   │   └── learning_session.py     # Learning sessions (scope, goal, user link)
│   │
│   ├── migrations/                 # Alembic migration scripts
│   │   └── versions/
│   │
│   ├── api/                        # FastAPI route modules
│   │   ├── __init__.py
│   │   ├── repositories.py         # CRUD: register repos, list, delete, trigger indexing
│   │   ├── analysis.py             # Trigger structural analysis, get status, get results
│   │   ├── profiles.py             # CRUD: user profiles
│   │   ├── sessions.py             # CRUD: learning sessions, trigger generation
│   │   ├── content.py              # Fetch chapters, diagrams, search
│   │   ├── graph.py                # Graph data endpoints (nodes, edges, subgraphs)
│   │   └── ws.py                   # WebSocket: pipeline progress streaming
│   │
│   ├── ingestion/                  # Layer 1: code parsing and file discovery
│   │   ├── __init__.py
│   │   ├── git_client.py           # Git operations (file listing, root detection)
│   │   ├── tree_sitter_parser.py   # Multi-language AST parsing
│   │   ├── language_heuristics.py  # File categorization rules
│   │   └── file_processor.py       # Orchestrates discovery → parse → extract
│   │
│   ├── graph/                      # Layer 1: graph construction and analysis
│   │   ├── __init__.py
│   │   ├── builder.py              # AST → NetworkX graph (imports, calls, inheritance)
│   │   ├── centrality.py           # PageRank, betweenness, community detection
│   │   ├── serialization.py        # NetworkX ↔ SQLite save/load
│   │   ├── queries.py              # Graph query helpers (subgraph extraction, paths)
│   │   └── scope.py                # Scope resolution (cluster, directory, full repo → subgraph)
│   │
│   ├── agents/                     # Layer 2: LLM agent pipeline
│   │   ├── __init__.py
│   │   ├── base.py                 # Shared agent infrastructure (tool abstraction)
│   │   ├── planner.py              # Planner agent: scoped graph → chapter outline
│   │   ├── writer.py               # Writer agent: chapter outline → personalized markdown
│   │   ├── verifier.py             # Verifier agent: checks claims against graph/AST
│   │   ├── summarizer.py           # Summarizer agent: chapter → Continuity Ledger entry
│   │   ├── canon_pack.py           # Canon Pack generation (includes user profile)
│   │   ├── continuity_ledger.py    # Sliding context state across chapters and sessions
│   │   └── prompts.py              # All prompt templates
│   │
│   ├── providers/                  # LLM provider abstraction
│   │   ├── __init__.py
│   │   ├── base.py                 # Abstract provider interface
│   │   ├── openai.py               # OpenAI provider
│   │   ├── anthropic.py            # Anthropic Claude provider
│   │   ├── google.py               # Google Gemini provider
│   │   └── registry.py             # Provider factory and tier assignment
│   │
│   ├── pipeline/                   # Orchestrates both layers
│   │   ├── __init__.py
│   │   ├── structural.py           # Layer 1 orchestrator (ingestion → graph → analysis)
│   │   ├── narrative.py            # Layer 2 orchestrator (scope → agents → chapters)
│   │   └── tasks.py                # arq task definitions (background jobs)
│   │
│   └── vector/                     # LanceDB integration
│       ├── __init__.py
│       └── store.py                # Embedding storage and semantic search
│
├── frontend/
│   ├── package.json
│   ├── tsconfig.json
│   ├── vite.config.ts
│   ├── index.html
│   ├── tailwind.config.ts
│   │
│   └── src/
│       ├── main.tsx                # React entry point
│       ├── App.tsx                 # Root component, routing
│       │
│       ├── api/                    # API client (typed fetch wrappers)
│       │   └── client.ts
│       │
│       ├── pages/                  # Top-level route pages
│       │   ├── Dashboard.tsx       # Repository list, repo cards with analysis status
│       │   ├── ArchitectureMap.tsx # Interactive graph explorer (the landing experience)
│       │   ├── ProfileSetup.tsx    # User profile creation/editing
│       │   ├── SessionCreate.tsx   # Scope selection + goal for new learning session
│       │   ├── SessionView.tsx     # Session content: chapter navigation + reading
│       │   └── Chapter.tsx         # Individual chapter view
│       │
│       ├── components/             # Reusable UI components
│       │   ├── Layout.tsx          # Shell: sidebar, header, content area
│       │   ├── Sidebar.tsx         # Session/chapter navigation, repo switcher
│       │   ├── GraphView.tsx       # React Flow / D3 graph visualization
│       │   ├── ScopeSelector.tsx   # Click-to-select communities/directories on the map
│       │   ├── MarkdownRenderer.tsx# Markdown display with Shiki + Mermaid
│       │   ├── ProgressTracker.tsx # Pipeline progress (WebSocket-driven)
│       │   └── CodeBlock.tsx       # Syntax-highlighted code with file links
│       │
│       └── hooks/                  # Custom React hooks
│           ├── useRepository.ts
│           ├── useProfile.ts
│           ├── useSession.ts
│           └── usePipelineProgress.ts
│
└── tests/
    ├── conftest.py                 # Shared fixtures
    ├── test_ingestion/
    ├── test_graph/
    ├── test_agents/
    ├── test_pipeline/
    └── test_api/
```

---

## 5. Layer 1 — Structural Analysis (No LLM)

Structural analysis runs per-repository, triggered by the admin. It produces the architecture map and graph data that all users share. This layer involves zero LLM calls and zero API cost.

### 5.1 Phase 1: Ingestion (Tree-Sitter AST Parsing)

#### 5.1.1 Overview

The ingestion phase transforms a raw Git repository into structured AST data. Every tracked file is discovered via Git, classified by language-specific heuristics, and parsed into an AST using tree-sitter.

#### 5.1.2 File Discovery

The `git_client.py` module wraps Git commands (via `subprocess`) to:

1. Locate the repository root (`git rev-parse --show-toplevel`).
2. List all tracked + untracked non-ignored files (`git ls-files --cached --others --exclude-standard`).
3. Read file contents as bytes for tree-sitter parsing.

#### 5.1.3 Language Detection and Heuristics

The `language_heuristics.py` module classifies files:

- **Supported languages (v1):** Python, JavaScript/TypeScript, Java, C#, Go, C/C++.
- Each language defines: manifest files, source extensions, entry-point signal filenames, ignored directories.
- **Auto-detection**: The primary language of a repository is detected by counting files per extension family and selecting the dominant language. Multi-language repositories use the union of relevant heuristics.

File classification produces four categories:


| Category   | Description                              | Example                                |
| ---------- | ---------------------------------------- | -------------------------------------- |
| `CONTEXT`  | High-value documentation files           | README.md, ARCHITECTURE.md, Dockerfile |
| `MANIFEST` | Dependency/build configuration           | package.json, pyproject.toml, go.mod   |
| `SIGNAL`   | Entry points and key orchestration files | main.py, index.ts, app.go              |
| `SOURCE`   | Regular source code files                | Any file matching language extensions  |


#### 5.1.4 Tree-Sitter Parsing

For each source file, tree-sitter produces a full AST. The parser module:

1. Loads the appropriate language grammar based on file extension.
2. Parses the file contents into a tree-sitter `Tree`.
3. Walks the tree to extract **structural entities**:
  - **Declarations:** classes, functions, methods, interfaces, structs, enums, type aliases
  - **Imports:** module imports, from-imports, require calls, use statements
  - **Exports:** exported symbols (where applicable)
  - **Call sites:** function/method invocations (for building the call graph)
  - **Inheritance:** class extends/implements relationships

Each entity is stored as a structured record with: file path, entity kind, entity name, start line, end line, and (for imports/calls) the target symbol name.

#### 5.1.5 Language Grammar Bundles

Tree-sitter grammars are installed as Python packages (`tree-sitter-python`, `tree-sitter-javascript`, `tree-sitter-typescript`, `tree-sitter-java`, `tree-sitter-c-sharp`, `tree-sitter-go`, `tree-sitter-c`, `tree-sitter-cpp`). These are pure-Python or pre-compiled shared objects, no external binaries required. They ship inside the Docker image.

### 5.2 Phase 2: Graph Construction (NetworkX)

#### 5.2.1 Overview

The extracted AST entities from Phase 1 are assembled into a **directed graph** using NetworkX. This graph is the single source of truth for all structural relationships in the codebase.

#### 5.2.2 Node Types


| Node type  | Represents                           | Key attributes                                                 |
| ---------- | ------------------------------------ | -------------------------------------------------------------- |
| `module`   | A single source file                 | path, language, line_count, category                           |
| `class`    | A class/struct/interface declaration | name, file_path, start_line, end_line                          |
| `function` | A function/method declaration        | name, file_path, start_line, end_line, is_method, parent_class |


#### 5.2.3 Edge Types


| Edge type   | Source → Target         | Derived from                             |
| ----------- | ----------------------- | ---------------------------------------- |
| `imports`   | module → module         | Import statements resolved to file paths |
| `contains`  | module → class/function | Declarations within a file               |
| `calls`     | function → function     | Call-site extraction from AST            |
| `inherits`  | class → class           | Extends/implements relationships         |
| `member_of` | function → class        | Method belonging to a class              |


#### 5.2.4 Import Resolution

Import resolution is the most language-specific part of graph construction. For each language, the builder implements a resolver that maps import strings to file paths:

- **Python:** `from foo.bar import Baz` → resolve `foo/bar.py` or `foo/bar/__init__.py` relative to project root or known source roots.
- **JavaScript/TypeScript:** `import { X } from './services/auth'` → resolve relative paths, check for `.ts`, `.tsx`, `.js`, `.jsx`, `/index.ts` variants.
- **Java:** `import com.example.service.OrderService` → map package path to `com/example/service/OrderService.java`.
- **Go:** `import "github.com/org/repo/pkg/auth"` → map to `pkg/auth/` directory.
- **C#:** `using Company.Project.Services` → map namespace to directory structure (heuristic, not 1:1 in C#).
- **C/C++:** `#include "auth/handler.h"` → resolve relative to include paths.

Unresolvable imports (external packages, standard library) are recorded as `external` nodes but excluded from centrality calculations.

#### 5.2.5 Serialization (NetworkX ↔ SQLite)

The graph is serialized to two SQLite tables:

`**graph_nodes`:**


| Column        | Type    | Description                                                                                               |
| ------------- | ------- | --------------------------------------------------------------------------------------------------------- |
| id            | TEXT PK | Unique node identifier (e.g., `module:src/auth/service.py` or `func:src/auth/service.py::validate_token`) |
| repository_id | TEXT FK | Parent repository                                                                                         |
| node_type     | TEXT    | `module`, `class`, `function`                                                                             |
| name          | TEXT    | Human-readable name                                                                                       |
| file_path     | TEXT    | Source file path                                                                                          |
| start_line    | INTEGER | Nullable, for classes/functions                                                                           |
| end_line      | INTEGER | Nullable                                                                                                  |
| attributes    | JSON    | Flexible extra data                                                                                       |


`**graph_edges`:**


| Column        | Type    | Description                                             |
| ------------- | ------- | ------------------------------------------------------- |
| repository_id | TEXT FK | Parent repository                                       |
| source_id     | TEXT FK | Source node                                             |
| target_id     | TEXT FK | Target node                                             |
| edge_type     | TEXT    | `imports`, `calls`, `inherits`, `contains`, `member_of` |
| attributes    | JSON    | Flexible extra data                                     |


Loading back: read tables → reconstruct `nx.DiGraph` with all attributes. This is ~50 lines of code and runs in milliseconds for graphs under 100K nodes.

### 5.3 Phase 3: Centrality Analysis (Core 20% Identification)

#### 5.3.1 Overview

The goal is to algorithmically identify the **architecturally significant subset** of the codebase — the core modules, classes, and functions that a new engineer must understand to be productive.

#### 5.3.2 Algorithms

Three complementary metrics are computed on the module-level subgraph (collapsing classes/functions into their parent files):

1. **PageRank** — identifies modules that are widely depended upon (high "authority"). Core data models, shared utilities, and foundational services score highest.
2. **Betweenness centrality** — identifies modules that act as bridges between clusters. Middleware, adapters, and orchestration layers score highest.
3. **Community detection (Louvain method)** — partitions the graph into clusters of tightly coupled modules. Each community roughly corresponds to a subsystem or domain area (e.g., "auth," "database," "API routes").

#### 5.3.3 Scoring

Each module receives a composite **architectural significance score**:

```
score = (0.5 × normalized_pagerank) + (0.3 × normalized_betweenness) + (0.2 × category_boost)
```

Where `category_boost` applies heuristic weights: SIGNAL files get a boost (entry points), CONTEXT files are always included, MANIFEST files are always included.

Modules are ranked by score. The **top 20%** (configurable threshold) are flagged as **core modules**. The community assignments determine which thematic cluster each module belongs to.

#### 5.3.4 Community Labeling

Each detected community is auto-labeled based on its dominant file paths and directory structure. For example, a cluster whose files are mostly under `src/billing/` and `src/payments/` is labeled "billing/payments." These labels appear on the architecture map and as scope options when creating learning sessions.

#### 5.3.5 Persistence

Results are stored in the `analysis_results` SQLite table:


| Column          | Type    |
| --------------- | ------- |
| node_id         | TEXT FK |
| repository_id   | TEXT FK |
| pagerank        | REAL    |
| betweenness     | REAL    |
| composite_score | REAL    |
| community_id    | INTEGER |
| community_label | TEXT    |
| is_core         | BOOLEAN |


---

## 6. User Profiles

### 6.1 Overview

A User Profile is a structured representation of an engineer's background. It persists across all learning sessions and is injected into every agent prompt to personalize the generated content.

### 6.2 Profile Structure

```python
class UserProfile(BaseModel):
    id: str                                     # UUID
    display_name: str
    languages: list[LanguageProficiency]
    frameworks: list[str]                       # e.g., ["Spring Boot", "Hibernate", "Kafka"]
    tools: list[str]                            # e.g., ["Docker", "Kubernetes", "PostgreSQL"]
    years_of_experience: int | None
    role: str | None                            # e.g., "backend", "frontend", "platform", "data", "fullstack"
    additional_context: str | None              # free-form, e.g., "I've never worked with event-driven architectures"

class LanguageProficiency(BaseModel):
    language: str                               # e.g., "Java", "Python", "Go"
    level: str                                  # "beginner", "intermediate", "advanced", "expert"
```

### 6.3 How Profiles Drive Personalization

The user profile is embedded in the Canon Pack for every learning session. This changes the Writer agent's behavior without any special ontology or mapping system — the LLM naturally adapts:

- **Known languages at expert level:** The Writer draws explicit parallels. "FastAPI's `Depends()` is the equivalent of Spring's `@Autowired`."
- **Unknown languages:** The Writer explains language-specific concepts from first principles, using the user's strongest language as the reference frame.
- **Known frameworks/tools:** The Writer skips explaining concepts the user already knows under a different name and focuses on the differences.
- **Experience level:** A junior developer gets more foundational context. A staff engineer gets architectural rationale and trade-off analysis.
- **Role context:** A platform engineer gets infrastructure-focused content. A frontend developer gets API contract and integration-focused content.

This approach leverages the LLM's inherent knowledge of cross-language parallels rather than maintaining an explicit mapping ontology. The profile is a prompt-level feature, not an algorithmic one.

---

## 7. Learning Sessions

### 7.1 Overview

A Learning Session is the unit of personalized content generation. It combines a user profile, a repository, a scope, and a goal. Each session produces a set of chapters tailored to that specific context.

### 7.2 Session Structure

```python
class LearningSession(BaseModel):
    id: str                                     # UUID
    user_profile_id: str                        # FK to UserProfile
    repository_id: str                          # FK to Repository
    scope_type: str                             # "full_repo", "community", "directory"
    scope_value: str | None                     # community_id, directory path, or None for full repo
    goal: str | None                            # free-form, e.g., "I need to work on the billing service"
    status: str                                 # "pending", "generating", "completed", "failed"
    created_at: datetime
    completed_at: datetime | None
```

### 7.3 Scope Resolution

When a user creates a session, the scope determines which portion of the graph the agent pipeline operates on:


| Scope type  | What it selects                              | Typical use                                              |
| ----------- | -------------------------------------------- | -------------------------------------------------------- |
| `full_repo` | The entire graph, with focus on the core 20% | "Give me the big picture of this system"                 |
| `community` | All modules in a detected community cluster  | "Teach me about the billing subsystem"                   |
| `directory` | All modules under a specific directory path  | "Explain services/auth/ and how it connects to the rest" |


In all cases, the **Planner agent receives the scoped subgraph plus awareness of the broader graph** — it knows what's outside the scope and how the scope connects to the rest of the system. This lets the Writer reference external dependencies without trying to explain them in full: "The billing service publishes events to the event bus (covered separately), which routes them to..."

### 7.4 Cross-Session Continuity

The Continuity Ledger is scoped per **user + repository** combination, not per session. This means:

1. User creates Session 1: "billing subsystem overview" → generates 8 chapters, Ledger entries 1-8.
2. User creates Session 2: "event bus deep dive" → the Planner and Writer receive Ledger entries 1-8 from Session 1. The new content says "as we saw in the billing guide..." rather than re-explaining billing concepts.
3. Session 3 builds on Sessions 1 and 2, and so on.

This creates a **cumulative learning experience** — each session builds on everything the user has already read for that repository.

The Ledger is append-only and ordered by session creation time. If the Ledger grows too large for the context window, the most recent entries are included in full, and older entries are included as compressed summaries.

---

## 8. Layer 2 — Narrative Generation (LLM-Powered)

### 8.1 Overview

The agent pipeline transforms the graph analysis into human-readable narrative documentation, personalized to the requesting user. Four agents operate in sequence, coordinated by the pipeline orchestrator. Each agent is a Pydantic AI `Agent` instance with typed inputs, typed outputs, and tool access.

The pipeline is triggered when a user creates a Learning Session.

### 8.2 Shared Infrastructure

#### 8.2.1 Tool Abstraction

All agent-to-external-data interactions go through a `Tool` protocol:

```python
class Tool(Protocol):
    name: str
    description: str
    input_schema: type[BaseModel]
    output_schema: type[BaseModel]

    async def execute(self, input: BaseModel) -> BaseModel: ...
```

Tools available to agents:


| Tool                    | Description                                                             |
| ----------------------- | ----------------------------------------------------------------------- |
| `read_file`             | Read a source file's contents (full or line range)                      |
| `get_node_info`         | Get a graph node's attributes, edges, and centrality scores             |
| `get_subgraph`          | Extract a subgraph around a node (N-hop neighborhood)                   |
| `search_symbols`        | Search for symbols by name/pattern across the graph                     |
| `get_community_members` | List all modules in a given community cluster                           |
| `get_call_chain`        | Trace the call chain from function A to function B                      |
| `verify_edge`           | Confirm whether an edge (import, call, inheritance) exists in the graph |


This abstraction is backed by direct Python function calls in v1. In a future version, these can be exposed as MCP servers without changing agent code.

#### 8.2.2 Canon Pack

Before any drafting begins, the Planner agent generates a **Canon Pack** — an immutable JSON document that governs all subsequent writing. It now includes the user profile for personalization:

```python
class CanonPack(BaseModel):
    project_name: str
    one_line_description: str
    primary_language: str
    architectural_style: str                    # e.g., "monolithic Django app", "FastAPI microservice"
    key_technologies: list[str]
    module_glossary: dict[str, str]             # canonical name → description for every core module in scope
    pattern_glossary: dict[str, str]            # e.g., "Repository Pattern" → how it's used here
    tone: str                                   # e.g., "authoritative, precise, developer-centric"
    terminology_rules: list[str]                # e.g., "Always refer to X as 'the Auth Service'"
    scope_description: str                      # what this session covers and how it fits in the broader system
    user_profile: UserProfileSummary            # embedded user background for personalization
    personalization_directives: list[str]       # e.g., "Draw parallels to Java/Spring Boot when explaining Python/FastAPI concepts"

class UserProfileSummary(BaseModel):
    known_languages: list[str]                  # e.g., ["Java (expert)", "SQL (advanced)"]
    known_frameworks: list[str]                 # e.g., ["Spring Boot", "Hibernate"]
    experience_level: str                       # e.g., "senior (6 years)"
    target_language: str                        # the primary language of the scoped codebase
    language_gap: str                           # e.g., "User is expert in Java but beginner in Python"
```

The Canon Pack is injected into every Writer and Verifier prompt as immutable context. It is never modified after creation.

#### 8.2.3 Continuity Ledger

A rolling summary that maintains narrative state across chapters and sessions:

```python
class LedgerEntry(BaseModel):
    session_id: str
    chapter_index: int
    chapter_title: str
    key_concepts_introduced: list[str]
    modules_covered: list[str]
    cross_language_mappings: list[str]          # e.g., ["Explained FastAPI Depends() ≈ Spring @Autowired"]
    forward_references: list[str]               # topics mentioned but not yet explained
    narrative_position: str                     # 1-2 sentence summary of where the story is
```

After each chapter is written, the Summarizer agent compresses it into a `LedgerEntry`. The Writer agent for the next chapter receives the Canon Pack + the full Continuity Ledger (all entries from the current session, plus entries from prior sessions for this user+repo combination) + the relevant source files.

### 8.3 Agent 1: Planner

**Input:** Scoped graph data (subgraph for the selected scope), centrality analysis, community assignments, repository context files (README, etc.), user profile, existing Continuity Ledger (from prior sessions).

**Output (structured):**

```python
class DocumentPlan(BaseModel):
    canon_pack: CanonPack
    chapters: list[ChapterPlan]

class ChapterPlan(BaseModel):
    index: int
    title: str
    summary: str                                # 2-3 sentences on what this chapter covers
    core_modules: list[str]                     # file paths of core modules to cover
    supporting_modules: list[str]               # file paths of supporting context
    graph_context: list[str]                    # specific graph queries the Writer should run
    depends_on_chapters: list[int]              # chapters that should be read first
    personalization_notes: str                  # guidance for the Writer on how to tailor this chapter
```

**Behavior:** The Planner uses a **frontier-tier** model. It examines the scoped graph structure, community clusters, and centrality scores to determine the optimal chapter ordering. Foundational modules (high PageRank, few dependencies) are placed first. Complex orchestration modules (high betweenness, many dependencies) come later.

The Planner is aware of the user profile and prior session content (via the Continuity Ledger). It avoids planning chapters that substantially duplicate previously covered material. If the user already learned about the database layer in a prior session, the Planner references it rather than re-covering it.

If a `full_repo` scope is selected, the Planner focuses on the core 20% and organizes chapters by community cluster. If a `community` or `directory` scope is selected, the Planner covers the scoped area in detail with awareness of how it connects to the broader system.

### 8.4 Agent 2: Writer

**Input (per chapter):** Canon Pack (with user profile), Continuity Ledger (all entries across sessions), the `ChapterPlan` for this chapter, full source content of `core_modules` and `supporting_modules`.

**Output:** Markdown string (the chapter body, starting at H3 level).

**Behavior:** The Writer uses a **frontier-tier** model. It produces narrative technical documentation following the style guide and personalization directives in the Canon Pack. It must:

- Draw explicit parallels to the user's known languages and frameworks when introducing new concepts.
- Skip explaining concepts the user already knows; focus on what's different or specific to this codebase.
- Cite specific files, line ranges, and symbols by name.
- Explain architectural decisions and patterns, not just describe what code does.
- Connect this chapter to previously covered material (via the Continuity Ledger), including material from prior sessions.
- Use fenced code blocks with language tags for code excerpts.
- Generate Mermaid diagram blocks where architectural relationships benefit from visualization.
- Flag any uncertainty with `[VERIFY]` markers for the Verifier to check.

The Writer has access to `read_file`, `get_node_info`, `get_subgraph`, and `get_call_chain` tools to fetch additional context during generation.

### 8.5 Agent 3: Verifier

**Input:** The Writer's draft markdown, the Canon Pack, and access to the graph + AST tools.

**Output (structured):**

```python
class VerificationResult(BaseModel):
    passed: bool
    violations: list[Violation]

class Violation(BaseModel):
    location: str                               # paragraph or sentence reference
    claim: str                                  # the specific technical claim
    violation_type: str                         # "nonexistent_symbol", "incorrect_edge", "terminology_mismatch", "unsupported_claim"
    evidence: str                               # what the graph/AST actually shows
    suggested_fix: str                          # how to correct the claim
```

**Behavior:** The Verifier uses a **fast-tier** model. It:

1. Extracts every technical entity mentioned in the draft (class names, function names, file paths, import relationships, call claims).
2. For each entity, queries the graph via `verify_edge`, `get_node_info`, and `search_symbols` to confirm existence and correctness.
3. Checks all terminology against the Canon Pack's glossary and terminology rules.
4. Validates that cross-language parallels are reasonable (e.g., the Writer didn't claim two unrelated concepts are equivalent).
5. Returns a structured list of violations.

If violations are found, the Writer rewrites only the affected sections (bounded correction, not full regeneration). This loop runs at most **3 iterations** per chapter before accepting the best version.

### 8.6 Agent 4: Summarizer

**Input:** The final (verified) chapter markdown and the existing Continuity Ledger.

**Output:** A new `LedgerEntry` for this chapter.

**Behavior:** The Summarizer uses a **fast-tier** model. It reads the completed chapter and produces a compressed summary capturing: which concepts were introduced, which modules were covered, which cross-language mappings were established, which forward references were made (topics hinted at but not explained), and a one-sentence narrative position summary.

### 8.7 Pipeline Flow

```
for each chapter in plan.chapters (sequential):
    1. Writer generates draft (personalized to user profile)
         ↓
    2. Verifier checks draft
         ↓
    3. If violations found and iterations < 3:
         Writer rewrites violated sections → go to step 2
         ↓
    4. Summarizer compresses chapter → append to Continuity Ledger
         ↓
    5. Store final chapter markdown + ledger entry in SQLite
         ↓
    6. Emit progress event via WebSocket
```

Chapters are generated **sequentially** because each chapter's Continuity Ledger entry feeds into the next chapter's context. This is a fundamental constraint of the consistency architecture.

### 8.8 LLM Provider Tier Assignment


| Tier         | Used by              | Default models                          | Purpose                                               |
| ------------ | -------------------- | --------------------------------------- | ----------------------------------------------------- |
| **Frontier** | Planner, Writer      | Claude Sonnet, GPT-4o, Gemini Pro       | High-quality reasoning, personalized prose generation |
| **Fast**     | Verifier, Summarizer | Claude Haiku, GPT-4o-mini, Gemini Flash | Mechanical extraction and compression                 |


Users configure their API key(s) and select a provider. The system automatically assigns tiers. Users can override globally ("use Sonnet for everything") or per-tier via environment variables:

```
SENTIAL_FRONTIER_PROVIDER=anthropic
SENTIAL_FRONTIER_MODEL=claude-sonnet-4-20250514
SENTIAL_FAST_PROVIDER=anthropic
SENTIAL_FAST_MODEL=claude-haiku-3-20250801
SENTIAL_ANTHROPIC_API_KEY=sk-...
```

---

## 9. Deterministic Diagram Generation

### 9.1 Overview

Architecture diagrams are generated **from the graph data, not by the LLM**. This eliminates hallucination risk entirely and produces diagrams that are provably accurate reflections of the codebase.

### 9.2 Diagram Types


| Diagram                     | Source data                                           | Format                                                |
| --------------------------- | ----------------------------------------------------- | ----------------------------------------------------- |
| **Module dependency graph** | NetworkX edges (imports) among core modules           | Interactive (React Flow) on the Architecture Map page |
| **Community cluster map**   | Louvain community assignments + inter-community edges | Interactive (React Flow) with color-coded clusters    |
| **Class hierarchy**         | Inheritance edges within a community                  | Mermaid `classDiagram` embedded in chapter markdown   |
| **Sequence diagrams**       | Call chains between key functions (from graph paths)  | Mermaid `sequenceDiagram` embedded in chapters        |
| **Module-level overview**   | High-level subsystem view (communities as supernodes) | Mermaid `flowchart` or interactive                    |


### 9.3 Generation

The backend exposes endpoints that return graph data in frontend-consumable format:

- `/api/repositories/{id}/graph/full` — full module-level graph (nodes + edges) for the Architecture Map.
- `/api/repositories/{id}/graph/community/{cid}` — subgraph for a specific community cluster.
- `/api/repositories/{id}/graph/neighborhood/{node}` — N-hop neighborhood of a specific module.

Mermaid blocks for chapters are generated by a deterministic Python function (not an LLM) that takes a subgraph and outputs Mermaid syntax. The Writer agent can request Mermaid blocks via the `get_subgraph` tool, and the tool returns both the graph data and a pre-rendered Mermaid string.

---

## 10. Backend API Design

### 10.1 REST Endpoints

**Repositories (admin-managed):**


| Method | Path                                  | Description                                       |
| ------ | ------------------------------------- | ------------------------------------------------- |
| POST   | `/api/repositories`                   | Register a new repository (local path or Git URL) |
| GET    | `/api/repositories`                   | List all registered repositories                  |
| GET    | `/api/repositories/{id}`              | Get repository details and analysis status        |
| DELETE | `/api/repositories/{id}`              | Remove a repository and its analysis data         |
| POST   | `/api/repositories/{id}/index`        | Trigger structural analysis (Layer 1)             |
| GET    | `/api/repositories/{id}/index/status` | Get indexing status and progress                  |


**User Profiles:**


| Method | Path                 | Description               |
| ------ | -------------------- | ------------------------- |
| POST   | `/api/profiles`      | Create a new user profile |
| GET    | `/api/profiles`      | List all profiles         |
| GET    | `/api/profiles/{id}` | Get a single profile      |
| PUT    | `/api/profiles/{id}` | Update a profile          |
| DELETE | `/api/profiles/{id}` | Delete a profile          |


**Learning Sessions:**


| Method | Path                                  | Description                                               |
| ------ | ------------------------------------- | --------------------------------------------------------- |
| POST   | `/api/sessions`                       | Create a new learning session (triggers Layer 2 pipeline) |
| GET    | `/api/sessions`                       | List sessions (filterable by profile_id, repository_id)   |
| GET    | `/api/sessions/{id}`                  | Get session details, status, and chapter list             |
| GET    | `/api/sessions/{id}/chapters`         | List all chapters for a session                           |
| GET    | `/api/sessions/{id}/chapters/{index}` | Get a single chapter's markdown content                   |
| GET    | `/api/sessions/{id}/canon-pack`       | Get the session's Canon Pack                              |


**Graph & Analysis (from Layer 1 structural data):**


| Method | Path                                               | Description                               |
| ------ | -------------------------------------------------- | ----------------------------------------- |
| GET    | `/api/repositories/{id}/graph/full`                | Full module-level graph for visualization |
| GET    | `/api/repositories/{id}/graph/community/{cid}`     | Subgraph for a community                  |
| GET    | `/api/repositories/{id}/graph/neighborhood/{node}` | N-hop neighborhood of a node              |
| GET    | `/api/repositories/{id}/analysis/centrality`       | Centrality scores and core module list    |
| GET    | `/api/repositories/{id}/analysis/communities`      | Community assignments and labels          |


**Continuity:**


| Method | Path                                            | Description                                        |
| ------ | ----------------------------------------------- | -------------------------------------------------- |
| GET    | `/api/profiles/{pid}/repositories/{rid}/ledger` | Full Continuity Ledger for a user+repo combination |


### 10.2 WebSocket


| Path                                   | Description                             |
| -------------------------------------- | --------------------------------------- |
| `/ws/repositories/{id}/index/progress` | Real-time structural analysis progress  |
| `/ws/sessions/{id}/progress`           | Real-time narrative generation progress |


Events emitted:

```python
class ProgressEvent(BaseModel):
    phase: str          # "ingestion", "graph", "centrality" (Layer 1) or "planning", "writing", "verification" (Layer 2)
    status: str         # "started", "progress", "completed", "failed"
    detail: str         # human-readable description
    progress: float     # 0.0 to 1.0
    chapter_index: int | None
```

---

## 11. Frontend Architecture

### 11.1 Pages

**Dashboard (`/`)** — Lists all indexed repositories with status cards (indexed, indexing, pending). Admin can register new repositories and trigger indexing. Users see the repo landscape at a glance.

**Architecture Map (`/repo/{id}/map`)** — **The primary landing experience for each repository.** Interactive dependency graph with community clusters color-coded and labeled. Nodes sized by centrality. Users orient themselves here before generating any content. The map supports:

- Zoom, pan, and filtering by community.
- Clicking a community cluster to see its details (modules, centrality scores, connections to other clusters).
- A "Start Learning Session" action from a selected cluster or from the full repo.

**Profile Setup (`/profile`)** — Create or edit the user profile. Structured form with language proficiency selectors, framework/tool tags, experience level, role, and optional free-form context.

**Session Creation (`/repo/{id}/learn`)** — Scope selection interface. Users can:

- Select "Full repo overview" for a high-level guide.
- Click a community cluster on an embedded mini-map to scope to that subsystem.
- Type a directory path to scope to a specific directory.
- Describe their goal in free-form text.
- See their profile summary (what the system knows about their background).

**Session View (`/session/{id}`)** — Displays generated content for a session. Sidebar shows chapter list with completion status. Main area renders the selected chapter. Progress tracker shown during generation.

**Chapter View (`/session/{id}/chapter/{index}`)** — Renders a single chapter's markdown with:

- Shiki syntax highlighting for code blocks.
- Mermaid.js rendering for diagram blocks.
- Clickable file paths that link to the Architecture Map focused on that module.
- Cross-language parallel callouts visually highlighted.

### 11.2 Key Interactions

- **Structural analysis progress**: When an admin triggers indexing, the ProgressTracker connects via WebSocket and displays real-time phase updates.
- **Session generation progress**: When a user starts a learning session, chapters stream in one by one via WebSocket. The user can start reading Chapter 1 while Chapter 3 is still generating.
- **Architecture Map → Session**: Users can select a cluster on the map and click "Learn about this" to create a session pre-scoped to that cluster.
- **Chapter → Map linking**: File paths in chapters are clickable and navigate to the Architecture Map centered on that node. Graph nodes are clickable and show which sessions/chapters reference that module.
- **Session history**: Users see their prior sessions for a repo, providing a learning timeline. They can revisit any session's content.

### 11.3 Build

The frontend is built with Vite into static assets (`dist/`). During Docker build, these are copied into the backend's static file directory. FastAPI serves them via `StaticFiles` mount at `/`. API routes are prefixed with `/api/` to avoid collision.

---

## 12. Data Model (SQLite Schema)

All application data lives in a single SQLite database file (default: `data/sential.db`).

### repositories


| Column           | Type      | Description                                |
| ---------------- | --------- | ------------------------------------------ |
| id               | TEXT PK   | UUID                                       |
| name             | TEXT      | Repository display name                    |
| path             | TEXT      | Local filesystem path to the repository    |
| primary_language | TEXT      | Detected primary language                  |
| index_status     | TEXT      | `pending`, `indexing`, `indexed`, `failed` |
| created_at       | TIMESTAMP |                                            |
| last_indexed_at  | TIMESTAMP | Nullable                                   |


### files


| Column        | Type    | Description                                               |
| ------------- | ------- | --------------------------------------------------------- |
| id            | TEXT PK | `{repository_id}:{relative_path}`                         |
| repository_id | TEXT FK |                                                           |
| relative_path | TEXT    | Path within the repository                                |
| language      | TEXT    | Detected language                                         |
| category      | TEXT    | CONTEXT, MANIFEST, SIGNAL, SOURCE                         |
| line_count    | INTEGER |                                                           |
| content_hash  | TEXT    | SHA-256 of file contents (for future incremental updates) |


### graph_nodes

(See section 5.2.5)

### graph_edges

(See section 5.2.5)

### analysis_results

(See section 5.3.5)

### user_profiles


| Column              | Type      | Description                                             |
| ------------------- | --------- | ------------------------------------------------------- |
| id                  | TEXT PK   | UUID                                                    |
| display_name        | TEXT      |                                                         |
| languages           | JSON      | List of `{language, level}` objects                     |
| frameworks          | JSON      | List of framework/tool strings                          |
| tools               | JSON      | List of tool strings                                    |
| years_of_experience | INTEGER   | Nullable                                                |
| role                | TEXT      | Nullable (backend, frontend, platform, data, fullstack) |
| additional_context  | TEXT      | Nullable, free-form                                     |
| created_at          | TIMESTAMP |                                                         |
| updated_at          | TIMESTAMP |                                                         |


### learning_sessions


| Column          | Type      | Description                                                    |
| --------------- | --------- | -------------------------------------------------------------- |
| id              | TEXT PK   | UUID                                                           |
| user_profile_id | TEXT FK   |                                                                |
| repository_id   | TEXT FK   |                                                                |
| scope_type      | TEXT      | `full_repo`, `community`, `directory`                          |
| scope_value     | TEXT      | Nullable (community_id, directory path, or null for full_repo) |
| goal            | TEXT      | Nullable, user-provided goal description                       |
| status          | TEXT      | `pending`, `generating`, `completed`, `failed`                 |
| created_at      | TIMESTAMP |                                                                |
| completed_at    | TIMESTAMP | Nullable                                                       |
| error           | TEXT      | Nullable                                                       |


### chapters


| Column                | Type      | Description                                    |
| --------------------- | --------- | ---------------------------------------------- |
| id                    | TEXT PK   | UUID                                           |
| session_id            | TEXT FK   | Learning session this chapter belongs to       |
| repository_id         | TEXT FK   |                                                |
| index                 | INTEGER   | Chapter ordering (1-based) within the session  |
| title                 | TEXT      |                                                |
| plan                  | JSON      | The `ChapterPlan` from the Planner             |
| content               | TEXT      | Final markdown content                         |
| status                | TEXT      | pending, writing, verifying, completed, failed |
| verification_attempts | INTEGER   |                                                |
| created_at            | TIMESTAMP |                                                |


### canon_packs


| Column     | Type    | Description                                         |
| ---------- | ------- | --------------------------------------------------- |
| id         | TEXT PK | UUID                                                |
| session_id | TEXT FK | Learning session                                    |
| data       | JSON    | The full Canon Pack (includes user profile summary) |


### continuity_ledger


| Column          | Type      | Description                           |
| --------------- | --------- | ------------------------------------- |
| id              | TEXT PK   | UUID                                  |
| user_profile_id | TEXT FK   | Scoped per user                       |
| repository_id   | TEXT FK   | Scoped per repo                       |
| session_id      | TEXT FK   | Which session produced this entry     |
| chapter_index   | INTEGER   |                                       |
| data            | JSON      | The `LedgerEntry`                     |
| created_at      | TIMESTAMP | Ordering for cross-session continuity |


---

## 13. Configuration

All configuration is via environment variables, loaded by `pydantic-settings`:


| Variable                        | Required    | Default                  | Description                             |
| ------------------------------- | ----------- | ------------------------ | --------------------------------------- |
| `SENTIAL_DATA_DIR`              | No          | `./data`                 | Directory for SQLite and LanceDB files  |
| `SENTIAL_REDIS_URL`             | Yes         | `redis://localhost:6379` | Redis connection string                 |
| `SENTIAL_HOST`                  | No          | `0.0.0.0`                | Backend listen host                     |
| `SENTIAL_PORT`                  | No          | `8000`                   | Backend listen port                     |
| `SENTIAL_FRONTIER_PROVIDER`     | Yes         | —                        | `openai`, `anthropic`, or `google`      |
| `SENTIAL_FRONTIER_MODEL`        | Yes         | —                        | Model name for frontier tier            |
| `SENTIAL_FAST_PROVIDER`         | No          | (same as frontier)       | Provider for fast tier                  |
| `SENTIAL_FAST_MODEL`            | No          | (auto-select)            | Model name for fast tier                |
| `SENTIAL_OPENAI_API_KEY`        | Conditional | —                        | Required if provider is `openai`        |
| `SENTIAL_ANTHROPIC_API_KEY`     | Conditional | —                        | Required if provider is `anthropic`     |
| `SENTIAL_GOOGLE_API_KEY`        | Conditional | —                        | Required if provider is `google`        |
| `SENTIAL_LOG_LEVEL`             | No          | `info`                   | Logging level                           |
| `SENTIAL_CORE_THRESHOLD`        | No          | `0.2`                    | Top N% of modules considered "core"     |
| `SENTIAL_MAX_VERIFY_ITERATIONS` | No          | `3`                      | Max Writer ↔ Verifier loops per chapter |


---

## 14. Docker & Deployment

### 14.1 Dockerfile (multi-stage)

```dockerfile
# Stage 1: Build frontend
FROM node:22-alpine AS frontend-build
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ .
RUN npm run build

# Stage 2: Python backend + static assets
FROM python:3.12-slim AS runtime
WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Install Python dependencies
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

# Copy backend code
COPY backend/ backend/
COPY alembic.ini .
COPY backend/migrations/ backend/migrations/

# Copy frontend build
COPY --from=frontend-build /app/frontend/dist backend/static

# Runtime config
ENV SENTIAL_HOST=0.0.0.0
ENV SENTIAL_PORT=8000
EXPOSE 8000

CMD ["uv", "run", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 14.2 docker-compose.yml

```yaml
services:
  sential:
    build: .
    ports:
      - "8000:8000"
    volumes:
      - sential-data:/app/data
      - /path/to/repos:/repos:ro   # mount repositories read-only
    environment:
      SENTIAL_REDIS_URL: redis://redis:6379
      SENTIAL_FRONTIER_PROVIDER: anthropic
      SENTIAL_FRONTIER_MODEL: claude-sonnet-4-20250514
      SENTIAL_ANTHROPIC_API_KEY: ${SENTIAL_ANTHROPIC_API_KEY}
    depends_on:
      - redis

  redis:
    image: redis:7-alpine
    volumes:
      - redis-data:/data

volumes:
  sential-data:
  redis-data:
```

---

## 15. Testing Strategy


| Layer                 | Framework                           | Approach                                                                                                                        |
| --------------------- | ----------------------------------- | ------------------------------------------------------------------------------------------------------------------------------- |
| **Unit tests**        | pytest + pytest-asyncio             | Test graph builder, centrality calculations, import resolution, serialization, scope resolution, Mermaid generation             |
| **Agent tests**       | pytest + Pydantic AI test utilities | Mock LLM responses, verify structured output parsing, test tool invocation logic, test personalization directives in Canon Pack |
| **API tests**         | pytest + httpx (AsyncClient)        | Test all REST endpoints (profiles, sessions, repositories, graph) with in-memory SQLite                                         |
| **Integration tests** | pytest                              | End-to-end: structural analysis + session generation on small fixture repositories                                              |
| **Frontend tests**    | Vitest + React Testing Library      | Component tests for rendering, interaction, scope selection                                                                     |
| **E2E tests**         | Playwright (later, not v1 blocker)  | Full browser tests against running Docker stack                                                                                 |


---

## 16. Implementation Order

The implementation is broken into 9 sequential milestones. Each milestone produces a working, testable increment.

### Milestone 1: Project Scaffolding

- Initialize Python project with uv, pyproject.toml
- Initialize React frontend with Vite, Tailwind, TanStack Query
- FastAPI app skeleton with health check
- Dockerfile and docker-compose.yml
- SQLite connection setup (aiosqlite)
- Alembic migration for core schema (repositories, user_profiles, learning_sessions, files, graph tables, chapters, canon_packs, continuity_ledger)
- CI: linting (ruff), type checking (pyright), test runner (pytest)

### Milestone 2: Ingestion Pipeline (Layer 1, Part 1)

- Git client (file listing, root detection)
- Language heuristics (file categorization)
- Implement tree-sitter parsing for Python and JavaScript/TypeScript (two languages first)
- Extract declarations, imports, exports, call sites
- Store file records in SQLite
- Unit tests for parsing and extraction

### Milestone 3: Graph Construction & Analysis (Layer 1, Part 2)

- NetworkX graph builder from extracted entities
- Import resolution for Python and JS/TS
- Centrality analysis (PageRank, betweenness, Louvain)
- Community labeling (auto-label from dominant file paths)
- Graph ↔ SQLite serialization
- Core module identification
- Scope resolution module (full_repo, community, directory → subgraph)
- API endpoints: repositories CRUD, trigger indexing, graph data, analysis results
- WebSocket for structural analysis progress
- Unit tests for graph builder, centrality, serialization, scope resolution

### Milestone 4: Architecture Map Frontend

- Dashboard page (list repos, register new, trigger indexing)
- Architecture Map page (React Flow graph visualization with community clusters)
- Community detail view (click cluster → see modules, centrality, connections)
- WebSocket-driven progress tracker for indexing
- This milestone delivers a usable product: structural analysis + interactive architecture map

### Milestone 5: User Profiles & Session Infrastructure

- Profile CRUD API + frontend (ProfileSetup page)
- Learning session data model and CRUD API
- Session creation frontend (SessionCreate page with scope selector + mini-map)
- arq task infrastructure for background narrative generation

### Milestone 6: Agent Pipeline (Planner + Writer)

- Pydantic AI setup, provider abstraction (OpenAI, Anthropic, Google)
- Tool abstraction layer
- Planner agent: scoped graph + user profile → DocumentPlan (Canon Pack + chapter plans)
- Writer agent: chapter plan + Canon Pack + Continuity Ledger → personalized markdown
- Canon Pack generation (with user profile embedding)
- Continuity Ledger implementation (per user+repo, cross-session)
- API endpoints: trigger session generation, get chapters
- WebSocket progress streaming for session generation

### Milestone 7: Verifier + Summarizer

- Verifier agent: draft → structured violation list
- Writer ↔ Verifier correction loop (max 3 iterations)
- Summarizer agent: chapter → LedgerEntry (with cross-language mapping tracking)
- End-to-end test: structural analysis → session creation → personalized guide

### Milestone 8: Session Frontend

- Session View page (chapter navigation + reading)
- Chapter View with Shiki + Mermaid rendering
- Clickable file paths linking chapters ↔ Architecture Map
- Session history (list prior sessions per user+repo)
- Cross-language parallel callouts styled in the markdown renderer

### Milestone 9: Remaining Languages + Polish

- Add tree-sitter parsing + import resolution for: Java, Go, C#, C/C++
- Test against real repositories in each language
- Error handling and recovery (pipeline resume on failure)
- Rate limiting and retry logic for LLM API calls
- Logging and observability
- Documentation (README, deployment guide)
- Performance optimization (large repos)
- LanceDB integration for semantic search (contextual features)

---

## 17. What Is Explicitly NOT in V1

These features are deferred to v2+ to keep scope manageable:


| Feature                                        | Reason for deferral                                                                                    |
| ---------------------------------------------- | ------------------------------------------------------------------------------------------------------ |
| **LSP integration**                            | Heavy per-language operational burden; tree-sitter provides sufficient structural data for v1          |
| **Git churn / hotspot analysis**               | Valuable but not essential when graph centrality already identifies core modules                       |
| **Cross-language semantic ontology**           | Personalization works through LLM prompt injection using the user profile; no explicit ontology needed |
| **MCP protocol**                               | Tool abstraction layer is designed to support MCP later; direct Python calls are simpler for v1        |
| **Incremental regeneration**                   | V1 does full regen; SQLite stores file hashes for future diffing                                       |
| **Global refinement pass (Critic agent)**      | The Verifier per-chapter loop provides sufficient quality; full-document Critic adds latency           |
| **Export to static site**                      | The web app IS the product; static export is a convenience feature for later                           |
| **Multi-user auth / RBAC**                     | Self-hosted, single-tenant for v1; profiles exist but there's no authentication layer                  |
| **Contextual chat ("ask about the codebase")** | LanceDB is included in the stack for this; the feature layers on after core pipeline ships             |
| **Scheduled/automatic re-indexing**            | Admin triggers indexing manually in v1; scheduled jobs are a v2 convenience                            |


---

## 18. Key Design Decisions & Rationale


| Decision                                                     | Rationale                                                                                                                                                                                                                                                      |
| ------------------------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Two-layer architecture (structural + narrative)**          | Structural analysis is cheap, shared, and always-on. Narrative generation is expensive, personalized, and on-demand. Separating them means the architecture map is instant for all users, and LLM costs are incurred only when someone actually needs a guide. |
| **User profiles drive personalization via prompt injection** | The LLM already knows cross-language parallels (Java ↔ Python, Spring ↔ FastAPI). Embedding the user's background in the Canon Pack lets the Writer naturally adapt without maintaining an explicit mapping ontology. Simple, effective, and zero maintenance. |
| **Continuity Ledger scoped per user+repo**                   | Cross-session continuity creates a cumulative learning experience. The second session builds on the first. This is the key differentiator from static documentation generators.                                                                                |
| **Scope selection as a first-class concept**                 | A 1M LOC monorepo can't be meaningfully covered in one guide. Letting users scope to a cluster/directory makes guides focused and actionable. The graph provides the broader awareness the Planner needs.                                                      |
| **Architecture map as the landing experience**               | Users orient before they read. The map shows what exists, what's central, and how things connect — all without a single LLM call. This is the hook that draws users in and the foundation they build learning sessions on.                                     |
| **Python over TypeScript**                                   | Superior AI/ML ecosystem (Pydantic AI, tree-sitter bindings, NetworkX). Structured output validation is native. Docker deployment eliminates Python's distribution weaknesses.                                                                                 |
| **NetworkX (in-memory) + SQLite**                            | Graph algorithms run in-memory for speed; persistence is a single file. No external database server to manage. Scales to 100K+ node graphs comfortably.                                                                                                        |
| **LanceDB (embedded) over hosted vector DB**                 | Zero server dependency. Runs in-process. Persists to disk. Fits the self-hosted, single-Docker-image deployment model.                                                                                                                                         |
| **Sequential chapter generation**                            | Each chapter's Continuity Ledger entry feeds the next. Parallelizing would break narrative coherence. The bottleneck is LLM latency, not local computation.                                                                                                    |
| **Deterministic diagrams from graph, not LLM**               | Eliminates diagram hallucination entirely. The graph is the ground truth; diagrams are projections of it.                                                                                                                                                      |
| **Verifier with bounded retries (max 3)**                    | Prevents infinite correction loops. After 3 iterations, accept the best version — diminishing returns on additional passes.                                                                                                                                    |
| **arq over Celery**                                          | Lightweight, async-native, minimal config. Celery is overkill for a single-tenant application.                                                                                                                                                                 |
| **React + Vite**                                             | Proven ecosystem, fast iteration. Interactive graph visualization (React Flow) is React-native. Clear separation between backend (Python) and frontend (TypeScript).                                                                                           |
| **uv over pip/poetry**                                       | 10-100x faster dependency resolution, deterministic lockfiles, modern ergonomics. Actively maintained by Astral (ruff team).                                                                                                                                   |


