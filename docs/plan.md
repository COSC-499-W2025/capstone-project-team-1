# Resume Artifact Generation — Implementation Plan

**Date:** Feb 4, 2026
**Owner:** Shlok
**Goal:** Standalone CLI that accepts a ZIP of git repos, runs the full existing analysis pipeline, then generates resume-worthy artifacts via a 4-pass local LLM pipeline.

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [What We Reuse (Zero Rewrite)](#2-what-we-reuse-zero-rewrite)
3. [What We Build (New Code)](#3-what-we-build-new-code)
4. [Ollama Structured Output — How It Works](#4-ollama-structured-output--how-it-works)
5. [Tree-sitter Integration](#5-tree-sitter-integration)
6. [The 4-Pass Pipeline — Detailed Design](#6-the-4-pass-pipeline--detailed-design)
7. [Pydantic Schemas (Structured Output Contracts)](#7-pydantic-schemas-structured-output-contracts)
8. [Prompt Templates](#8-prompt-templates)
9. [CLI Design (Typer)](#9-cli-design-typer)
10. [Implementation Order](#10-implementation-order)
11. [File Structure](#11-file-structure)
12. [Dependencies to Add](#12-dependencies-to-add)
13. [Models & Hardware](#13-models--hardware)
14. [Risk & Mitigations](#14-risk--mitigations)
15. [Open Questions (Deferred)](#15-open-questions-deferred)

---

## 1. Architecture Overview

```
ZIP file
   │
   ▼
┌──────────────────────────────────────────────────────┐
│  EXISTING CODE (import & call)                       │
│                                                      │
│  extract_zip_to_persistent_location(zip_path, id)    │
│            │                                         │
│            ▼                                         │
│  discover_git_repos(extraction_dir)                  │
│            │                                         │
│            ▼  (for each repo)                        │
│  getRepoStats(repo_path) → RepoStat                 │
│  getUserRepoStats(repo_path, email) → UserRepoStats  │
│  collect_user_additions(repo_path, email) → List[str]│
│  DeepRepoAnalyzer.analyze() → skills + insights     │
│                                                      │
└──────────────────────────────────────────────────────┘
   │
   │  All existing data collected per repo:
   │  - repo_stats (languages, frameworks, commits, health)
   │  - user_stats (contribution %, frequency, date range)
   │  - user_additions (raw code diffs, oldest→newest)
   │  - skills (ExtractedSkill objects)
   │  - insights (Insight objects)
   │
   ▼
┌──────────────────────────────────────────────────────┐
│  NEW CODE — Resume Generation Pipeline               │
│                                                      │
│  Pass 1: File Discovery (rank files by importance)   │
│  Pass 2: File Analysis (tree-sitter + LLM per file)  │
│  Pass 3: Project Synthesis (resume bullets per repo) │
│  Pass 4: Portfolio Synthesis (unified profile)       │
│                                                      │
└──────────────────────────────────────────────────────┘
   │
   ▼
┌──────────────────────────────────────────────────────┐
│  OUTPUT                                              │
│  - Print to terminal (rich formatting)               │
│  - Write to JSON file (optional)                     │
│  - Write to Markdown file (optional)                 │
└──────────────────────────────────────────────────────┘
```

---

## 2. What We Reuse (Zero Rewrite)

Every function below is imported and called as-is. We accept all side effects (SQLite writes, etc.).

### 2.1 ZIP Extraction

**Function:** `extract_zip_to_persistent_location(zip_path: str, zip_id: int) -> Path`
**File:** `src/artifactminer/api/analyze.py:214-258`

- Extracts to `./.extracted/{zip_id}/`
- Cleans up previous extractions at that ID
- Validates ZIP integrity
- **Side effects:** Creates directories on disk
- **Dependency quirk:** Raises `HTTPException` on failure — we'll catch this and convert to a CLI-friendly error

**Note:** This function expects a `zip_id` (int). For the CLI we'll just use `1` as a hardcoded ID since we're not going through the API. Or we hash the filename.

### 2.2 Git Repo Discovery

**Function:** `discover_git_repos(base_path: Path) -> List[Path]`
**File:** `src/artifactminer/api/analyze.py:111-138`

- Recursively finds all `.git` directories
- Deduplicates nested repos
- **Side effects:** None
- **Dependencies:** `isGitRepo` from `repo_intelligence_main`

### 2.3 Repo Statistics

**Function:** `getRepoStats(repo_path) -> RepoStats` (dataclass)
**File:** `src/artifactminer/RepositoryIntelligence/repo_intelligence_main.py`

- Returns: project_name, Languages, frameworks, first_commit, last_commit, total_commits, is_collaborative, health_score
- **Side effects:** None (pure function)

**Function:** `getUserRepoStats(repo_path, user_email) -> UserRepoStats` (dataclass)
**File:** `src/artifactminer/RepositoryIntelligence/repo_intelligence_user.py:31-72`

- Returns: project_name, total_commits, userStatspercentages, commitFrequency, first_commit, last_commit, commitActivities
- **Side effects:** Calls `collect_user_additions` internally for activity classification
- **Raises:** `ValueError` if email invalid

### 2.4 User Code Additions

**Function:** `collect_user_additions(repo_path, user_email, since=None, until="HEAD", max_commits=500, skip_merges=True, max_patch_bytes=200_000) -> List[str]`
**File:** `src/artifactminer/RepositoryIntelligence/repo_intelligence_user.py:92-146`

- Returns list of strings, one per commit, containing ONLY the user's added lines (no deletions, no headers)
- Ordered oldest→newest
- Validates email, filters by author, skips merges
- Caps patch size at 200KB per commit
- **Side effects:** None (reads git log)

### 2.5 Skill Extraction

**Class:** `DeepRepoAnalyzer`
**File:** `src/artifactminer/skills/deep_analysis.py:30-111`

- `analyze(repo_path, repo_stat, user_email, user_contributions, consent_level) -> DeepAnalysisResult`
- Returns: `skills: List[ExtractedSkill]` and `insights: List[Insight]`
- Each `ExtractedSkill` has: skill name, category, proficiency (float), evidence (list of strings)
- Each `Insight` has: title, evidence, why_it_matters
- **Side effects:** None

### 2.6 Persistence (Optional — we may skip for MVP)

We can optionally call `saveRepoStats`, `saveUserRepoStats`, `persist_extracted_skills`, `persist_insights_as_resume_items`, and `rank_projects` to populate the SQLite DB. This lets the existing TUI show results too. But it's not required for the CLI MVP.

**Decision:** Call them. It's free and lets us verify the existing pipeline still works. User said "ill delete the db lol."

### 2.7 Database Setup

The existing code uses SQLAlchemy + SQLite. We need the DB to be initialized before calling any persistence functions.

**Import:** `from artifactminer.db.database import SessionLocal, engine, Base`

```python
Base.metadata.create_all(bind=engine)  # Create tables if not exist
db = SessionLocal()
```

---

## 3. What We Build (New Code)

### 3.1 New Module: `src/artifactminer/resume/`

```
src/artifactminer/resume/
├── __init__.py
├── cli.py              # Typer CLI entry point
├── pipeline.py         # 4-pass orchestration
├── passes/
│   ├── __init__.py
│   ├── discovery.py    # Pass 1: File ranking
│   ├── analysis.py     # Pass 2: Per-file analysis (tree-sitter + LLM)
│   ├── synthesis.py    # Pass 3: Project-level resume bullets
│   └── portfolio.py    # Pass 4: Cross-repo portfolio synthesis
├── schemas.py          # Pydantic models for structured output
├── ollama_client.py    # Thin wrapper around ollama.chat with structured output
├── treesitter.py       # Tree-sitter code summarization
└── prompts.py          # Prompt templates for all 4 passes
```

### 3.2 New Module: `src/artifactminer/helpers/ollama_client.py` (Rewrite)

The existing `ollama_test.py` is just 16 lines of example code. The `get_ollama_response()` function is imported but **never defined** (critical bug in existing code). We write a proper client.

---

## 4. Ollama Structured Output — How It Works

### 4.1 Python API (ollama 0.6.1)

```python
from ollama import chat
from pydantic import BaseModel, Field

class ResumeProjectSummary(BaseModel):
    project_name: str = Field(..., description="Project name")
    one_liner: str = Field(..., description="One-sentence project summary")
    highlights: list[str] = Field(..., description="3-5 resume bullet points")
    skills: list[str] = Field(..., description="Technical skills demonstrated")

response = chat(
    model="qwen3:4b",
    messages=[{"role": "user", "content": prompt}],
    format=ResumeProjectSummary.model_json_schema(),  # <-- THE KEY
    options={"temperature": 0},
)

# response.message.content is a JSON string guaranteed to match the schema
parsed = ResumeProjectSummary.model_validate_json(response.message.content)
```

### 4.2 How It Works Under the Hood

- Ollama uses **constrained decoding** (grammar-based token sampling)
- The model physically **cannot** emit tokens that violate the JSON schema
- This means: no garbled JSON, no missing fields, no wrong types
- The `format` parameter accepts either `"json"` (freeform JSON) or a full JSON Schema object
- Pydantic's `.model_json_schema()` produces exactly the right format

### 4.3 Key Options

```python
options={
    "temperature": 0.1,      # Low for factual, deterministic output
    "num_ctx": 4096,          # Context window (tokens). Default varies by model.
    "num_predict": 1024,      # Max output tokens
    "seed": 42,               # Reproducibility (optional)
}
```

### 4.4 What the Existing Test Already Proves

File `tests/ollama/test_structured_output.py` already demonstrates this exact pattern:

```python
# Line 73-78 from existing test
response = chat(
    model=model,
    messages=[{"role": "user", "content": prompt}],
    format=ResumeProjectSummary.model_json_schema(),
    options={"temperature": 0},
)
parsed = ResumeProjectSummary.model_validate_json(response.message.content)
```

This test passes. The pattern is proven. We just need to use it with our own schemas and prompts.

### 4.5 Our Ollama Client Wrapper

```python
# src/artifactminer/resume/ollama_client.py

from typing import TypeVar, Type
from pydantic import BaseModel
from ollama import chat, ResponseError

T = TypeVar("T", bound=BaseModel)

DEFAULT_MODEL = "qwen3:4b"

def query_ollama(
    prompt: str,
    schema: Type[T],
    model: str = DEFAULT_MODEL,
    system: str | None = None,
    temperature: float = 0.1,
    num_ctx: int = 4096,
    num_predict: int = 1024,
) -> T:
    """
    Send a prompt to Ollama and get back a validated Pydantic object.

    Uses constrained decoding — the response is GUARANTEED to match the schema.
    No retry logic needed. No JSON parsing fallbacks needed.
    """
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    response = chat(
        model=model,
        messages=messages,
        format=schema.model_json_schema(),
        options={
            "temperature": temperature,
            "num_ctx": num_ctx,
            "num_predict": num_predict,
        },
    )

    return schema.model_validate_json(response.message.content)


def query_ollama_text(
    prompt: str,
    model: str = DEFAULT_MODEL,
    system: str | None = None,
    temperature: float = 0.3,
    num_ctx: int = 4096,
    num_predict: int = 2048,
) -> str:
    """
    Send a prompt to Ollama and get back raw text (no schema).

    Used for Pass 4 (portfolio synthesis) where we want free-form markdown,
    not structured JSON.
    """
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    response = chat(
        model=model,
        messages=messages,
        options={
            "temperature": temperature,
            "num_ctx": num_ctx,
            "num_predict": num_predict,
        },
    )

    return response.message.content
```

---

## 5. Tree-sitter Integration

### 5.1 Current State

- **Not installed.** Zero tree-sitter code exists in the Python codebase.
- `pyproject.toml` has no tree-sitter dependency.
- The `web-tree-sitter` JS package appears in `opentui-react-exp/bun.lock` but is unrelated.

### 5.2 What We Need

```
pip install tree-sitter tree-sitter-python tree-sitter-javascript tree-sitter-typescript tree-sitter-java tree-sitter-go tree-sitter-rust tree-sitter-c-sharp tree-sitter-ruby
```

Or more realistically for MVP: just Python and JavaScript/TypeScript since those are the most common student project languages.

### 5.3 What Tree-sitter Does for Us

Given raw source code, tree-sitter parses it into an AST and we extract a **structural summary**:

```python
# Input: 200 lines of Python code
# Output (tree-sitter summary): ~30 tokens

"""
File: src/api/routes.py
Classes: none
Functions: get_spaces(db: Session), create_reservation(db: Session, data: ReservationCreate), check_availability(space_id: int)
Imports: fastapi, sqlalchemy, pydantic
Decorators: @router.get, @router.post
"""
```

### 5.4 When to Use Tree-sitter

**Rule:** Always run tree-sitter for structural metadata. For token compression:
- User additions **under 150 lines**: send raw code + tree-sitter metadata header
- User additions **over 150 lines**: send tree-sitter structural summary only (no raw code)

### 5.5 Implementation

```python
# src/artifactminer/resume/treesitter.py

import tree_sitter_python as tspython
import tree_sitter_javascript as tsjavascript
import tree_sitter_typescript as tstypescript
from tree_sitter import Language, Parser

LANGUAGES = {
    ".py": Language(tspython.language()),
    ".js": Language(tsjavascript.language()),
    ".ts": Language(tstypescript.language_typescript()),
    ".tsx": Language(tstypescript.language_tsx()),
}

def get_structural_summary(code: str, file_ext: str) -> str | None:
    """
    Parse code with tree-sitter and return a concise structural summary.

    Returns None if the language isn't supported.
    """
    lang = LANGUAGES.get(file_ext)
    if not lang:
        return None

    parser = Parser(lang)
    tree = parser.parse(bytes(code, "utf-8"))
    root = tree.root_node

    classes = []
    functions = []
    imports = []

    for node in _walk(root):
        if node.type in ("class_definition", "class_declaration"):
            name = _get_name(node)
            if name:
                classes.append(name)
        elif node.type in ("function_definition", "function_declaration",
                           "method_definition", "arrow_function"):
            name = _get_name(node)
            if name:
                # Include parameters if available
                params = _get_params(node)
                functions.append(f"{name}({params})" if params else name)
        elif node.type in ("import_statement", "import_from_statement",
                           "import_declaration"):
            imports.append(node.text.decode("utf-8").strip())

    lines = []
    if classes:
        lines.append(f"Classes: {', '.join(classes)}")
    if functions:
        lines.append(f"Functions: {', '.join(functions)}")
    if imports:
        # Deduplicate and limit
        unique_imports = list(dict.fromkeys(imports))[:10]
        lines.append(f"Imports: {'; '.join(unique_imports)}")

    return "\n".join(lines) if lines else None
```

### 5.6 Language Support Priority

| Priority | Extension(s) | Package |
|----------|-------------|---------|
| P0 (MVP) | `.py` | `tree-sitter-python` |
| P0 (MVP) | `.js`, `.ts`, `.tsx` | `tree-sitter-javascript`, `tree-sitter-typescript` |
| P1 | `.java` | `tree-sitter-java` |
| P1 | `.go` | `tree-sitter-go` |
| P2 | `.rs`, `.rb`, `.cs` | respective packages |

For unsupported languages, we skip tree-sitter and send raw code (with line count capping).

---

## 6. The 4-Pass Pipeline — Detailed Design

### Overview

```
Pass 1: File Discovery
  Input:  file paths + sizes from user additions
  Output: ranked list of top N files to analyze
  LLM:    structured output (FileRanking schema)

Pass 2: File Analysis
  Input:  per-file user additions + tree-sitter metadata
  Output: per-file analysis (what was built, skills used)
  LLM:    structured output (FileAnalysis schema)

Pass 3: Project Synthesis
  Input:  all file analyses + repo metadata
  Output: project summary + resume bullet points
  LLM:    structured output (ProjectSummary schema)

Pass 4: Portfolio Synthesis
  Input:  all project summaries
  Output: unified developer profile + cross-repo themes
  LLM:    free-form text (markdown)
```

### Pass 1: File Discovery

**Goal:** Given a flat list of files the user touched, rank them by resume importance so we don't waste LLM context on boilerplate files.

**Input data available:**
- List of file paths from `collect_user_additions` (we can extract paths from the git diff)
- Lines of code per file (from the additions)

**Wait — we have a problem.** `collect_user_additions` returns one string per **commit**, not per **file**. The additions are concatenated code without file path metadata (the `extract_added_lines` function strips diff headers including file paths).

**Solution:** We need to modify our approach slightly. Instead of using `collect_user_additions` directly, we call `repo.git.show()` ourselves and preserve the file path metadata. OR we write a new helper that groups additions by file path.

**Implementation choice:** Write a new function `collect_user_additions_by_file()` that returns `Dict[str, str]` mapping `file_path → added_code`. This is a thin wrapper around the same git commands but preserves the `+++ b/path/to/file` headers.

```python
def collect_user_additions_by_file(
    repo_path: str,
    user_email: str,
    max_commits: int = 500,
) -> dict[str, str]:
    """
    Like collect_user_additions but groups additions by file path.
    Returns {file_path: added_lines_string} across all user commits.
    """
    # Same git walking logic as collect_user_additions
    # But parse the diff to extract file paths and group additions per file
    ...
```

**Pass 1 LLM call:**
- Input: list of (file_path, line_count) tuples
- Output: `FileRanking` schema — top N files ranked by importance
- This pass is cheap — small input, small output
- If total files <= 15, skip Pass 1 and analyze all files

### Pass 2: File Analysis

**Goal:** For each selected file, produce a structured analysis of what the user built.

**Input per file:**
- File path
- Tree-sitter structural summary (always)
- Raw user additions (if < 150 lines) OR tree-sitter summary only (if >= 150 lines)
- Repo context: project name, languages, frameworks

**Output per file:** `FileAnalysis` schema
- what_was_built: 1-2 sentence description
- technical_decisions: list of notable choices
- skills_demonstrated: list of skill names

**LLM call:** One call per file. Sequential (not parallel — Ollama is single-threaded).

### Pass 3: Project Synthesis

**Goal:** Combine all file analyses + repo metadata into resume-ready project bullets.

**Input:**
- All `FileAnalysis` results from Pass 2
- Repo metadata: project_name, languages, frameworks, total_commits, date range, contribution %
- Skills from existing `DeepRepoAnalyzer` (for cross-validation)

**Output:** `ProjectSummary` schema
- project_name
- one_liner: single sentence ("Built a campus resource tracker with FastAPI and React")
- bullet_points: 3-5 resume bullet points using action verbs
- technologies: deduplicated tech list
- impact_metrics: any quantifiable outputs (files changed, features built, etc.)

**Resume bullet format:** "Accomplished [X] as measured by [Y] by doing [Z]"
- Start with action verb (Developed, Implemented, Architected, Optimized, etc.)
- Include specific technologies
- Include quantifiable metrics where possible

### Pass 4: Portfolio Synthesis

**Goal:** Combine all project summaries into a unified developer profile.

**Input:**
- All `ProjectSummary` results from Pass 3
- Total contribution stats across repos

**Output:** Free-form markdown (not structured JSON)
- Professional summary paragraph (2-3 sentences)
- Top skills with evidence
- Cross-project themes (e.g., "consistently builds REST APIs", "strong testing culture")
- Career narrative suggestions

**Why free-form?** This is the "creative" pass. We want the LLM to write naturally, not fill JSON fields. Low temperature (0.3) still keeps it grounded.

---

## 7. Pydantic Schemas (Structured Output Contracts)

```python
# src/artifactminer/resume/schemas.py

from pydantic import BaseModel, Field

# --- Pass 1 ---

class RankedFile(BaseModel):
    file_path: str = Field(..., description="Path to the file")
    importance: int = Field(..., description="1=most important, higher=less important")
    reason: str = Field(..., description="Why this file matters for a resume")

class FileRanking(BaseModel):
    ranked_files: list[RankedFile] = Field(..., description="Files ranked by resume importance")


# --- Pass 2 ---

class FileAnalysis(BaseModel):
    file_path: str = Field(..., description="Path to the analyzed file")
    what_was_built: str = Field(..., description="1-2 sentence description of what this code does")
    technical_decisions: list[str] = Field(..., description="Notable technical choices (e.g., 'Used caching with TTL')")
    skills_demonstrated: list[str] = Field(..., description="Technical skills shown (e.g., 'REST API Design', 'SQLAlchemy ORM')")


# --- Pass 3 ---

class ProjectSummary(BaseModel):
    project_name: str = Field(..., description="Name of the project")
    one_liner: str = Field(..., description="Single sentence project description for resume header")
    bullet_points: list[str] = Field(..., description="3-5 resume bullet points starting with action verbs")
    technologies: list[str] = Field(..., description="Deduplicated list of technologies used")
    impact_metrics: list[str] = Field(
        default_factory=list,
        description="Quantifiable achievements (e.g., '8 API endpoints', '95% test coverage')"
    )


# --- Pass 4 is free-form markdown, no schema ---


# --- Final aggregate output ---

class ResumeArtifacts(BaseModel):
    """Top-level output containing all generated artifacts."""
    projects: list[ProjectSummary]
    portfolio_summary: str = Field(..., description="Free-form markdown portfolio summary")
    model_used: str = Field(..., description="Which Ollama model was used")
    generation_time_seconds: float = Field(..., description="Total pipeline duration")
```

---

## 8. Prompt Templates

### 8.1 System Prompt (Shared across all passes)

```
You are a professional resume writer and technical recruiter with expertise in
software engineering. You analyze code contributions and produce resume-ready
content. Be concise, factual, and achievement-oriented. Never fabricate skills
or accomplishments — only describe what is evident from the code.
```

### 8.2 Pass 1: File Discovery

```
Below is a list of files modified by a developer in the project "{project_name}".
Rank them by importance for a resume — which files best demonstrate technical
skill and accomplishment?

Files:
{file_list}

Rank the top {top_n} files. Prioritize:
- Core application logic over config/boilerplate
- Files with significant additions over minor edits
- Backend logic, algorithms, and architecture over styling/assets
```

### 8.3 Pass 2: File Analysis

```
Analyze this developer's code contribution to the file "{file_path}" in the
project "{project_name}" (a {languages} project using {frameworks}).

{tree_sitter_header}

Code additions by the developer:
```
{user_code}
```

Describe what was built, notable technical decisions, and skills demonstrated.
Be specific to the code — don't speculate beyond what's visible.
```

### 8.4 Pass 3: Project Synthesis

```
Synthesize a resume entry for the project "{project_name}".

Project metadata:
- Languages: {languages}
- Frameworks: {frameworks}
- User contribution: {contribution_pct}% of commits ({total_user_commits} commits)
- Date range: {first_commit} to {last_commit}
- Detected skills: {skills_list}

File-level analyses:
{file_analyses_json}

Generate:
1. A one-line project description (for resume header)
2. 3-5 bullet points starting with action verbs (Developed, Implemented, Architected, etc.)
3. Use the format: "[Action verb] [what] using [technology] [quantifiable result if available]"
4. Do not repeat the same verb in consecutive bullets
5. Technologies list (deduplicated)
```

### 8.5 Pass 4: Portfolio Synthesis

```
You are writing a developer portfolio summary based on analysis of multiple projects.

Project summaries:
{all_project_summaries}

Write a professional portfolio summary in markdown that includes:
1. A 2-3 sentence professional summary paragraph
2. A "Key Skills" section grouping skills by category
3. A "Cross-Project Themes" section identifying patterns across projects
4. Keep the tone professional but not generic — reference specific projects

The developer's strongest signal is: {top_skills}
```

---

## 9. CLI Design (Typer)

### 9.1 Entry Point

```bash
# Primary command
uv run python -m artifactminer.resume generate \
  --zip /path/to/projects.zip \
  --email "shlok@email.com" \
  --model "qwen3:4b"

# With options
uv run python -m artifactminer.resume generate \
  --zip /path/to/projects.zip \
  --email "shlok@email.com" \
  --model "qwen3:4b" \
  --output resume_output.json \
  --verbose
```

### 9.2 CLI Arguments

| Argument | Type | Required | Default | Description |
|----------|------|----------|---------|-------------|
| `--zip` | Path | Yes | — | Path to ZIP file containing git repos |
| `--email` | str | Yes | — | User's git email (for filtering commits) |
| `--model` | str | No | `qwen3:4b` | Ollama model to use |
| `--output` | Path | No | None | Write results to JSON file |
| `--markdown` | Path | No | None | Write results to markdown file |
| `--top-files` | int | No | 15 | Max files to analyze per repo |
| `--verbose` | bool | No | False | Print detailed progress |
| `--skip-db` | bool | No | False | Don't save to SQLite |

### 9.3 pyproject.toml Addition

```toml
[project.scripts]
# ... existing entries ...
resume = "artifactminer.resume.cli:app"
```

### 9.4 Progress Output

```
[1/5] Extracting ZIP...
  Found 3 git repositories

[2/5] Analyzing repositories (existing pipeline)...
  ✓ campus-tracker: 45 commits, 12 skills detected
  ✓ chat-app: 23 commits, 8 skills detected
  ✓ ml-pipeline: 67 commits, 15 skills detected

[3/5] Pass 1: Discovering important files...
  campus-tracker: 8 files selected (of 14)
  chat-app: 5 files selected (of 7)
  ml-pipeline: 12 files selected (of 20)

[4/5] Pass 2-3: Analyzing files and generating bullets...
  campus-tracker [1/8] src/api/routes.py ... done (4.2s)
  campus-tracker [2/8] src/services/availability.py ... done (3.8s)
  ...
  Synthesizing campus-tracker summary... done (5.1s)
  ...

[5/5] Pass 4: Building portfolio profile...
  done (6.3s)

════════════════════════════════════════════
RESUME ARTIFACTS
════════════════════════════════════════════

## Campus Resource Tracker
Built a full-stack campus resource management system with FastAPI and React...

• Developed 8 RESTful API endpoints for space management and reservations using FastAPI and SQLAlchemy
• Implemented real-time availability caching with TTL-based invalidation, reducing API latency
• Architected responsive dashboard with calendar integration and D3.js utilization charts
• Added comprehensive test coverage for API response validation and error handling
• Technologies: Python, FastAPI, SQLAlchemy, React, D3.js, TypeScript

...

## Portfolio Summary
[Generated markdown summary]

Total time: 4m 23s | Model: qwen3:4b
```

---

## 10. Implementation Order

### Phase 1: Scaffolding (Day 1)

| # | Task | Description |
|---|------|-------------|
| 1 | Create `src/artifactminer/resume/` package | Directory structure, `__init__.py` files |
| 2 | Implement `ollama_client.py` | `query_ollama()` and `query_ollama_text()` wrappers |
| 3 | Define `schemas.py` | All Pydantic models for structured output |
| 4 | Add `typer` to dependencies | Update `pyproject.toml` |
| 5 | Basic `cli.py` skeleton | Parse args, print "hello world" |
| 6 | Test `query_ollama()` | Verify structured output works with `qwen3:4b` |

### Phase 2: Pipeline Core (Day 2-3)

| # | Task | Description |
|---|------|-------------|
| 7 | Write `collect_user_additions_by_file()` | New helper that preserves file paths |
| 8 | Implement Pass 1 (discovery.py) | File ranking with LLM |
| 9 | Implement Pass 2 (analysis.py) | Per-file analysis (without tree-sitter first) |
| 10 | Implement Pass 3 (synthesis.py) | Project-level resume bullet generation |
| 11 | Implement Pass 4 (portfolio.py) | Cross-repo portfolio synthesis |
| 12 | Wire up `pipeline.py` | Orchestrate all 4 passes |
| 13 | Wire up `cli.py` | Full end-to-end: ZIP → extract → analyze → resume → print |

### Phase 3: Tree-sitter (Day 3-4)

| # | Task | Description |
|---|------|-------------|
| 14 | Add tree-sitter dependencies | `tree-sitter`, `tree-sitter-python`, `tree-sitter-javascript`, `tree-sitter-typescript` |
| 15 | Implement `treesitter.py` | `get_structural_summary()` function |
| 16 | Integrate into Pass 2 | Add tree-sitter metadata to file analysis prompts |
| 17 | Test with real repos | Verify quality improvement |

### Phase 4: Polish (Day 4-5)

| # | Task | Description |
|---|------|-------------|
| 18 | Output formatting | Rich terminal output, JSON export, Markdown export |
| 19 | Error handling | Ollama connection errors, empty repos, no user commits |
| 20 | End-to-end test | Full pipeline with a real ZIP file |
| 21 | Demo preparation | Clean output, timing, model comparison |

---

## 11. File Structure

```
src/artifactminer/resume/
├── __init__.py
├── cli.py                  # Typer app: `resume generate --zip ... --email ...`
├── pipeline.py             # ResumeGenerationPipeline class — orchestrates everything
├── passes/
│   ├── __init__.py
│   ├── discovery.py        # Pass 1: rank files by importance
│   ├── analysis.py         # Pass 2: per-file LLM analysis + tree-sitter
│   ├── synthesis.py        # Pass 3: project summary + resume bullets
│   └── portfolio.py        # Pass 4: cross-repo portfolio synthesis
├── schemas.py              # Pydantic models (FileRanking, FileAnalysis, ProjectSummary, etc.)
├── ollama_client.py        # query_ollama(prompt, schema, model) → T
├── treesitter.py           # get_structural_summary(code, ext) → str | None
├── prompts.py              # All prompt templates as constants
└── helpers.py              # collect_user_additions_by_file(), misc utilities
```

---

## 12. Dependencies to Add

```toml
# pyproject.toml additions
dependencies = [
  # ... existing ...
  "typer>=0.9",
  "rich>=13",                    # For terminal formatting (typer uses this)
  "tree-sitter>=0.24",
  "tree-sitter-python>=0.23",
  "tree-sitter-javascript>=0.23",
  "tree-sitter-typescript>=0.23",
]
```

**Note:** `tree-sitter` Python bindings underwent a major API change in v0.22+. The new API uses `Language(tree_sitter_python.language())` instead of the old `Language.build_library()` approach. The installed `tree-sitter` version must be >= 0.22.

---

## 13. Models & Hardware

### 13.1 Currently Installed on Machine

| Model | Size | Notes |
|-------|------|-------|
| `qwen3:4b` | 2.5 GB | **Our default.** Good at code, supports structured output |
| `lfm2.5-thinking:1.2b-bf16` | 2.3 GB | Non-transformer, thinking model. Experimental. |
| `lfm2.5-thinking:latest` | 731 MB | Quantized version. Very small. |

### 13.2 Recommended Models to Pull

```bash
# Best for code analysis (already installed!)
ollama pull qwen3:4b           # Already have this

# Alternative: Phi-4-mini — highest HumanEval score at this size
ollama pull phi4-mini           # ~2.5 GB, 128K context, MIT license

# If you want to compare with a bigger model
ollama pull qwen2.5-coder:7b   # ~5 GB, purpose-built for code
```

### 13.3 Model Selection Strategy

For MVP: use `qwen3:4b` (already installed, already working, supports structured output).

The `--model` flag lets us test other models without code changes.

### 13.4 Hardware Context (M2 MacBook Air, 8GB)

- macOS: ~3 GB
- Python + app: ~0.5 GB
- **Available for LLM: ~4-4.5 GB**
- `qwen3:4b` at Q4_K_M: 2.5 GB (comfortable)
- Expected speed: ~4-8 tokens/sec

### 13.5 Qwen3 Thinking Mode Note

Qwen3 has a "thinking" mode that can be controlled. For structured output, we want thinking **disabled** (faster, more deterministic). Passing low temperature and structured output format should handle this, but we may need to add `/no_think` to prompts or set `think=False` in options if available.

---

## 14. Risk & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Ollama not running | Low (MVP demo) | Fatal | Check `ollama.list()` at startup, print helpful error |
| Model not pulled | Medium | Fatal | Check model exists, offer to pull if missing |
| Empty user additions | Medium | Pass 2 has no input | Skip file, note in output |
| Very large repos (1000+ files) | Low | Slow Pass 1 | Cap at top 20 files, skip Pass 1 if < 15 files |
| Tree-sitter doesn't support language | Medium | No structural summary | Fall back to raw code with line count cap |
| LLM produces low-quality bullets | Medium | Bad demo | Low temperature + specific prompt constraints |
| `extract_zip_to_persistent_location` raises HTTPException | Certain | CLI crash | Catch HTTPException, convert to typer error |
| SQLite locked / DB issues | Low | Pipeline fails | Wrap all DB calls in try/except, continue without persistence |
| Qwen3 "thinking" mode activates | Medium | Slow + verbose output | Use `/no_think` directive in prompts or configure options |

---

## 15. Open Questions (Deferred)

These are explicitly deferred to post-MVP:

1. **Database schema for resume artifacts** — MVP prints to terminal / writes to file only
2. **TUI/CLI display in OpenTUI** — Build after pipeline works
3. **User editing/refinement** — Future feature
4. **Cloud API tier (OpenAI/Claude)** — Future feature
5. **Model tier selection UI** — MVP uses `--model` flag
6. **Retry/fallback on bad output** — Structured output eliminates this for JSON passes
7. **Caching/incremental analysis** — Future optimization
8. **Multi-user support** — Future feature
9. **Export to PDF/DOCX** — Future feature

---

## Appendix A: Existing Function Signatures (Quick Reference)

```python
# analyze.py
def extract_zip_to_persistent_location(zip_path: str, zip_id: int) -> Path
def discover_git_repos(base_path: Path) -> List[Path]
def get_user_email(db: Session) -> str
def get_consent_level(db: Session) -> str

# repo_intelligence_user.py
def collect_user_additions(
    repo_path: Pathish, user_email: str,
    since: Optional[str] = None, until: str = "HEAD",
    max_commits: int = 500, skip_merges: bool = True,
    max_patch_bytes: int = 200_000,
) -> List[str]
def getUserRepoStats(repo_path: Pathish, user_email: str) -> UserRepoStats
def extract_added_lines(patch_text: str) -> str

# repo_intelligence_main.py
def getRepoStats(repo_path) -> RepoStats
def isGitRepo(path) -> bool

# deep_analysis.py
class DeepRepoAnalyzer:
    def analyze(
        self, repo_path: str, repo_stat: Any,
        user_email: str, user_contributions: Dict | None = None,
        consent_level: str = "none",
    ) -> DeepAnalysisResult  # .skills: List[ExtractedSkill], .insights: List[Insight]

# ollama (library)
from ollama import chat
response = chat(
    model="qwen3:4b",
    messages=[{"role": "user", "content": "..."}],
    format=SomeSchema.model_json_schema(),  # structured output
    options={"temperature": 0.1, "num_ctx": 4096},
)
parsed = SomeSchema.model_validate_json(response.message.content)
```

## Appendix B: Key Data Flow Example

```python
# What the pipeline looks like in pseudocode

zip_path = "/path/to/portfolio.zip"
email = "shlok@example.com"
model = "qwen3:4b"

# Phase 1: Existing pipeline
extraction_dir = extract_zip_to_persistent_location(zip_path, zip_id=1)
repos = discover_git_repos(extraction_dir)

all_project_summaries = []

for repo_path in repos:
    # Existing analysis
    repo_stats = getRepoStats(repo_path)
    user_stats = getUserRepoStats(repo_path, email)
    additions_by_file = collect_user_additions_by_file(repo_path, email)  # NEW
    deep_result = DeepRepoAnalyzer(enable_llm=False).analyze(
        repo_path, repo_stats, email, {"additions": "\n".join(additions_by_file.values())}
    )

    # Pass 1: Discovery
    if len(additions_by_file) > 15:
        ranking = query_ollama(discovery_prompt, FileRanking, model)
        selected_files = ranking.ranked_files[:15]
    else:
        selected_files = list(additions_by_file.keys())

    # Pass 2: File Analysis
    file_analyses = []
    for file_path in selected_files:
        code = additions_by_file[file_path]
        ts_summary = get_structural_summary(code, Path(file_path).suffix)
        analysis = query_ollama(analysis_prompt, FileAnalysis, model)
        file_analyses.append(analysis)

    # Pass 3: Project Synthesis
    project_summary = query_ollama(synthesis_prompt, ProjectSummary, model)
    all_project_summaries.append(project_summary)

# Pass 4: Portfolio Synthesis
portfolio_text = query_ollama_text(portfolio_prompt, model)

# Output
print_results(all_project_summaries, portfolio_text)
```
