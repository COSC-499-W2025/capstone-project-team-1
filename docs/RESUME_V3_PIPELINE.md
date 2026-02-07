# Resume v3 Pipeline — Comprehensive Documentation

**Branch:** `experimental-llamacpp-v3`

**Status:** Production-ready, 45/45 unit tests passing

---

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Three Phases](#three-phases)
4. [Data Models](#data-models)
5. [Extractors](#extractors)
6. [LLM Queries](#llm-queries)
7. [Output Formats](#output-formats)
8. [Usage Guide](#usage-guide)
9. [Performance](#performance)

---

## Overview

The v3 resume pipeline rebuilds the resume generation system with a **clean three-phase architecture**:

```
                         ┌─────────────────────────────────────┐
                         │    INPUT: ZIP of git repos          │
                         └──────────────┬──────────────────────┘
                                        │
                         ┌──────────────▼──────────────────────┐
                         │  PHASE 1: EXTRACT                   │
                         │  (Static analysis, no LLM)          │
                         │                                     │
                         │  • README extraction               │
                         │  • Commit hybrid classification    │
                         │  • Directory structure scanning    │
                         │  • Code construct regex analysis   │
                         │  • Project type inference          │
                         │                                     │
                         │  Output: ProjectDataBundle +       │
                         │          PortfolioDataBundle       │
                         └──────────────┬──────────────────────┘
                                        │
                         ┌──────────────▼──────────────────────┐
                         │  PHASE 2: QUERY                     │
                         │  (Focused LLM calls)                │
                         │                                     │
                         │  • 1 call per project               │
                         │    (description + bullets +        │
                         │     narrative)                      │
                         │  • 3 calls for portfolio            │
                         │    (summary, skills, profile)      │
                         │                                     │
                         │  Output: ProjectSection objects     │
                         │          + portfolio text          │
                         └──────────────┬──────────────────────┘
                                        │
                         ┌──────────────▼──────────────────────┐
                         │  PHASE 3: ASSEMBLE                  │
                         │  (Pure formatting)                  │
                         │                                     │
                         │  • Stitch LLM responses into        │
                         │    markdown template                │
                         │  • Serialize to JSON structure      │
                         │                                     │
                         │  Output: ResumeOutput object        │
                         └──────────────┬──────────────────────┘
                                        │
                         ┌──────────────▼──────────────────────┐
                         │  OUTPUT                             │
                         │  • resume.md (human-readable)       │
                         │  • resume.json (structured data)    │
                         └─────────────────────────────────────┘
```

### Design Principles

1. **Separation of Concerns**: Each phase is independent — EXTRACT needs no LLM, QUERY is testable with mock data, ASSEMBLE is pure formatting.
2. **Graceful Degradation**: If LLM fails, static extractors still work; if commit classification fails, defaults to "feature".
3. **Token Efficiency**: Rich data extraction means smaller, more focused LLM prompts. Pre-digested facts instead of raw code.
4. **Testability**: All extractors are pure functions taking `repo_path` and returning structured data.

---

## Architecture

### Package Structure

```
src/artifactminer/resume/
├── llm_client.py              # REUSED: LLM server + OpenAI SDK
├── facts.py                   # REUSED: utility functions
├── generate.py                # REUSED: extract_zip, discover_git_repos
├── enhance.py                 # LEGACY: template-based fallback
├── cli.py                      # UPDATED: register v3 + v2 commands
├── __init__.py                 # UPDATED: export both pipelines
│
├── models.py                   # NEW: ProjectDataBundle, etc.
├── pipeline.py                 # NEW: main orchestrator
├── assembler.py                # NEW: markdown + JSON output
│
├── extractors/                 # NEW: static data extraction
│   ├── __init__.py
│   ├── readme.py               # README.md extraction
│   ├── commits.py              # Hybrid commit classification
│   ├── structure.py            # Directory & file grouping
│   ├── constructs.py           # Routes, classes, tests via regex
│   └── project_type.py         # Type inference (Web API, CLI, etc.)
│
└── queries/                    # NEW: LLM query layer
    ├── __init__.py
    ├── prompts.py              # Prompt templates
    └── runner.py               # LLM execution + parsing
```

### Call Stack

```
CLI: resume generate
  └─> pipeline.generate_resume_v3(zip_path, email, model)
        │
        ├─> PHASE 1: EXTRACT
        │   ├─> extract_zip(zip_path)
        │   ├─> discover_git_repos(extract_dir)
        │   └─> for each repo:
        │       ├─> getRepoStats() [EXISTING]
        │       ├─> getUserRepoStats() [EXISTING]
        │       ├─> DeepRepoAnalyzer.analyze() [EXISTING]
        │       ├─> extract_readme()
        │       ├─> extract_and_classify_commits()
        │       ├─> extract_structure()
        │       ├─> extract_constructs()
        │       ├─> infer_project_type()
        │       └─> assemble into ProjectDataBundle
        │
        ├─> build_portfolio() [aggregate bundles]
        │
        ├─> PHASE 2: QUERY
        │   ├─> for each project:
        │   │   └─> run_project_query(bundle, model)
        │   │       ├─> build_project_prompt()
        │   │       └─> query_llm_text()
        │   │           └─> parse DESCRIPTION/BULLETS/NARRATIVE
        │   │
        │   └─> run_portfolio_queries()
        │       ├─> query for professional summary
        │       ├─> query for skills section
        │       └─> query for developer profile
        │
        └─> PHASE 3: ASSEMBLE
            ├─> assemble_markdown(output)
            └─> assemble_json(output)
```

---

## Three Phases

### PHASE 1: EXTRACT

**Goal:** Gather rich, structured data from repositories using purely static analysis.

**No LLM involved.** Can run offline, on any machine.

#### Extractors

| Extractor | Input | Output | Purpose |
|-----------|-------|--------|---------|
| **readme.py** | Repo path | `str` (max 2000 chars) | Best source for "what is this project?" |
| **commits.py** | Repo path, user email | `List[CommitGroup]` | Semantic grouping (feature/bugfix/etc.) |
| **structure.py** | Repo path, user email | `(List[str], Dict[str, List[str]])` | Top-level dirs + user-touched files by module |
| **constructs.py** | Repo path, touched files | `CodeConstructs` | Routes, classes, test functions, key functions |
| **project_type.py** | Repo path, frameworks, README | `str` | Project type ("Web API", "CLI Tool", etc.) |

#### Extract Output

All data is collected into a **ProjectDataBundle**:

```python
@dataclass
class ProjectDataBundle:
    project_name: str
    project_path: str
    project_type: str                           # e.g. "Web API"

    # From existing analyzers
    languages: List[str]
    primary_language: Optional[str]
    frameworks: List[str]
    detected_skills: List[str]
    insights: List[Dict]

    # From NEW extractors
    readme_text: str                            # Full README excerpt
    commit_groups: List[CommitGroup]            # Grouped + classified
    directory_overview: List[str]               # Top-level dirs
    module_groups: Dict[str, List[str]]        # Dir → files user touched
    constructs: CodeConstructs                  # Routes, classes, tests, etc.
```

**Key insight**: The bundle contains **concrete data** — actual commit messages, actual route paths, actual class names — not abstractions or summaries. This makes LLM prompts extremely specific.

---

### PHASE 2: QUERY

**Goal:** Use focused LLM calls to generate compelling prose from the extracted data.

#### Per-Project Query

**Call budget**: 1 LLM call per project

**Input**:
```
build_project_prompt(ProjectDataBundle)
  → Produces a prompt containing:
    • Project name, type, tech stack
    • README excerpt (first 600 chars)
    • Commit messages grouped by type (showing actual commits)
    • Code constructs (routes, classes, tests, functions)
    • Modules the developer worked on
    • Skills detected + insights
```

**Output format** (strictly structured):
```
DESCRIPTION: [1-2 sentences about the project]
BULLETS:
- [achievement bullet 1]
- [achievement bullet 2]
- [achievement bullet 3]
NARRATIVE: [2-3 sentences about contribution and impact]
```

**Example**:
```
DESCRIPTION: A FastAPI REST API for task management with JWT authentication.
BULLETS:
- Implemented 3 user endpoints (GET, POST, DELETE) using FastAPI decorators
- Built JWT token generation and validation helpers for secure authentication
- Wrote comprehensive unit tests covering all route handlers and edge cases
NARRATIVE: Independently architected the entire API backend, handling authentication, database models, and test coverage with attention to error handling and type safety.
```

#### Portfolio Queries

**Call budget**: 3 LLM calls total (not per project)

1. **Professional Summary** (1 call)
   - Input: Project count, languages, frameworks, date range, project types
   - Output: 2-3 sentence career summary
   - Example: *"Full-stack developer with 5 years building REST APIs and web applications in Python and TypeScript, focused on scalable systems and test-driven development."*

2. **Skills Section** (1 call)
   - Input: All languages, frameworks, top skills from all projects
   - Output: Organized skills by category (Languages, Frameworks, Infrastructure, Practices)
   - Example:
     ```
     Languages: Python, TypeScript, JavaScript
     Frameworks & Libraries: FastAPI, SQLAlchemy, React
     Infrastructure: PostgreSQL, Docker, GitHub Actions
     Practices: Test-Driven Development, API Design, System Design
     ```

3. **Developer Profile** (1 call)
   - Input: Commit breakdown, project types, contribution %, skill range
   - Output: 3-4 sentence narrative about developer's strengths and growth
   - Example: *"Demonstrates strong backend expertise with consistent test coverage across all projects. Comfortable across the full stack (React, FastAPI, PostgreSQL). Shows growth from procedural scripts to scalable microservice architectures."*

#### LLM Query Flow

```
for each ProjectDataBundle:
  1. Call build_project_prompt(bundle)
  2. Call query_llm_text(prompt, model="qwen2.5-coder-3b-q4")
  3. Parse response using _parse_project_response()
     → Extract DESCRIPTION, BULLETS, NARRATIVE sections
  4. Store in ProjectSection object

Call run_portfolio_queries(portfolio):
  1. Query 1: build_summary_prompt() → professional_summary
  2. Query 2: build_skills_prompt() → skills_section
  3. Query 3: build_profile_prompt() → developer_profile
```

---

### PHASE 3: ASSEMBLE

**Goal:** Stitch LLM responses and extracted data into final markdown and JSON.

#### Markdown Assembly

```
assemble_markdown(output: ResumeOutput) → str
```

Produces a professional resume in markdown:

```markdown
# Technical Resume

## Professional Summary
[LLM-generated, 2-3 sentences]

## Technical Skills
Languages: Python, TypeScript, JavaScript
Frameworks & Libraries: FastAPI, SQLAlchemy, React
Infrastructure: PostgreSQL, Docker
Practices: Test-Driven Development, API Design

## Projects

### project-name
**Technologies:** FastAPI, SQLAlchemy | **Language:** Python | **Contribution:** 100%
**Period:** 2024-01-15 to 2024-06-20

[LLM: 1-2 sentence project description]

- [LLM: achievement bullet 1]
- [LLM: achievement bullet 2]
- [LLM: achievement bullet 3]

> [LLM: 2-3 sentence narrative]

## Developer Profile
[LLM-generated, 3-4 sentences]

---
*Generated with qwen2.5-coder-3b-q4 in 127s*
```

#### JSON Assembly

```
assemble_json(output: ResumeOutput) → str
```

Produces structured JSON for frontend consumption:

```json
{
  "professional_summary": "...",
  "skills_section": "...",
  "developer_profile": "...",
  "projects": [
    {
      "name": "project-name",
      "type": "Web API",
      "primary_language": "Python",
      "frameworks": ["FastAPI", "SQLAlchemy"],
      "contribution_pct": 100,
      "commit_breakdown": {
        "feature": 15,
        "bugfix": 3,
        "test": 2
      },
      "period": {
        "first_commit": "2024-01-15",
        "last_commit": "2024-06-20"
      },
      "description": "...",
      "bullets": ["...", "...", "..."],
      "narrative": "..."
    }
  ],
  "portfolio": {
    "total_projects": 5,
    "total_commits": 127,
    "languages_used": ["Python", "TypeScript"],
    "frameworks_used": ["FastAPI", "SQLAlchemy", "React"],
    "project_types": {"Web API": 2, "CLI Tool": 1, "Library": 2}
  },
  "metadata": {
    "model_used": "qwen2.5-coder-3b-q4",
    "generation_time_seconds": 127.3,
    "errors": []
  }
}
```

---

## Data Models

### ProjectDataBundle

Represents all extracted data for a single project.

```python
@dataclass
class ProjectDataBundle:
    # Identity
    project_name: str
    project_path: str
    project_type: str  # "Web API", "CLI Tool", "Library", etc.

    # Tech stack
    languages: List[str]
    language_percentages: List[float]
    primary_language: Optional[str]
    frameworks: List[str]

    # User contribution
    user_contribution_pct: Optional[float]
    user_total_commits: Optional[int]
    total_commits: Optional[int]
    first_commit: Optional[str]  # ISO date
    last_commit: Optional[str]    # ISO date

    # Extracted data
    readme_text: str
    commit_groups: List[CommitGroup]
    directory_overview: List[str]
    module_groups: Dict[str, List[str]]
    constructs: CodeConstructs

    # From existing analyzers
    detected_skills: List[str]
    skill_evidence: Dict[str, List[str]]
    insights: List[Dict[str, Any]]

    def all_commit_messages(self) -> List[str]
    def commit_count_by_type(self) -> Dict[str, int]
    def to_prompt_context(self) -> str  # Compact LLM context
```

### CommitGroup

Groups commits by semantic type with actual messages.

```python
@dataclass
class CommitGroup:
    category: str  # "feature" | "bugfix" | "refactor" | "test" | "docs" | "chore"
    messages: List[str]  # Actual commit messages

    @property
    def count(self) -> int
```

### CodeConstructs

Concrete code artifacts found via regex.

```python
@dataclass
class CodeConstructs:
    routes: List[str]           # e.g. ["GET /api/users", "POST /api/tasks"]
    classes: List[str]          # e.g. ["User", "TaskService"]
    test_functions: List[str]   # e.g. ["test_login", "test_create_user"]
    key_functions: List[str]    # e.g. ["authenticate", "serialize"]
```

### PortfolioDataBundle

Aggregated data across all projects.

```python
@dataclass
class PortfolioDataBundle:
    user_email: str
    projects: List[ProjectDataBundle]

    # Aggregations
    total_projects: int
    total_commits: int
    languages_used: List[str]
    frameworks_used: List[str]
    earliest_commit: Optional[str]
    latest_commit: Optional[str]
    project_types: Dict[str, int]  # {"Web API": 2, "CLI Tool": 1}
    top_skills: List[str]          # Deduplicated, frequency-sorted
```

### ProjectSection

LLM-generated content for one project.

```python
@dataclass
class ProjectSection:
    description: str = ""          # 1-2 sentences
    bullets: List[str] = []        # 3-5 achievement bullets
    narrative: str = ""            # 2-3 sentence contribution narrative
```

### ResumeOutput

Final output combining LLM responses with extracted data.

```python
@dataclass
class ResumeOutput:
    # Per-project LLM output
    project_sections: Dict[str, ProjectSection]

    # Portfolio-level LLM output
    professional_summary: str
    skills_section: str
    developer_profile: str

    # Data + metadata
    portfolio_data: Optional[PortfolioDataBundle]
    model_used: str
    generation_time_seconds: float
    errors: List[str]
```

---

## Extractors

### README Extractor

**File**: `extractors/readme.py`

**Purpose**: Extract the full README.md content as context for LLM.

**Algorithm**:
1. Look for common README names (README.md, readme.md, README.rst, etc.)
2. Read file in UTF-8 with error tolerance
3. Truncate to 2000 characters
4. Return empty string if not found

**Why this matters**: The README is the single best source for "what does this project do?" An LLM writing "This developer built a web API" without knowing it's a real-time task management system misses context. By including the README excerpt in the project prompt, the LLM can write descriptions like "This developer architected a real-time collaborative task management API, handling WebSocket connections and conflict-free data synchronization."

**Test coverage**: 3 tests
- Extracts README content ✓
- Respects max_chars truncation ✓
- Returns empty for missing README ✓

---

### Hybrid Commit Classifier

**File**: `extractors/commits.py`

**Purpose**: Classify commits into semantic types (feature/bugfix/refactor/test/docs/chore) to enable resume bullets like "Implemented 15 features and resolved 8 critical bugs."

**Architecture**:

```
Input: List of commit messages (for one user in one repo)
  │
  ├─> STAGE 1: Static Regex Classification
  │   ├─ Conventional-commit prefixes (feat:, fix:, test:, etc.)
  │   │  Example: "feat: add user login" → feature
  │   │
  │   └─ Keyword heuristics
  │      Example: "Add user authentication" → feature (keyword "add")
  │      Example: "Fix null pointer" → bugfix (keyword "fix")
  │      Example: "Refactor database pool" → refactor (keyword "refactor")
  │
  ├─ RESULT: ~70-80% of commits classified instantly
  │
  └─> STAGE 2: LLM Fallback (batched)
      ├─ Collect remaining unclassified commits
      ├─ Batch up to 50 at a time
      ├─ Send to LLM with structured JSON response schema
      ├─ Parse responses and accumulate breakdown
      │
      └─ RESULT: Near-100% classification
          (If LLM unavailable, unclassified default to "feature")
```

**Regex Rules**:

```python
CONVENTIONAL_COMMITS = {
    "feat": "feature",
    "fix": "bugfix",
    "refactor": "refactor",
    "test": "test",
    "docs": "docs",
    "chore": "chore",
}

KEYWORD_HEURISTICS = [
    (r"\b(add|implement|create)\b", "feature"),
    (r"\b(fix|resolve|patch)\b", "bugfix"),
    (r"\b(refactor|restructure)\b", "refactor"),
    (r"\b(test|spec|coverage)\b", "test"),
    (r"\b(doc|readme)\b", "docs"),
    (r"\b(bump|release|merge)\b", "chore"),
]
```

**LLM Fallback**:

For unclassified commits, batch up to 50 and query:
```
Classify each commit into one category (feature, bugfix, refactor, test, docs, chore):

1. Update user profile page
2. Handle edge case in auth
3. Add comprehensive test suite
...
```

Response schema:
```python
class SingleClassification(BaseModel):
    index: int
    category: str  # "feature" | "bugfix" | ...

class ClassificationBatch(BaseModel):
    classifications: list[SingleClassification]
```

**Output**:
```python
List[CommitGroup]
# Example:
[
    CommitGroup(category="feature", messages=[
        "implement user registration endpoint",
        "add task CRUD operations",
        "add JWT authentication",
    ]),
    CommitGroup(category="bugfix", messages=[
        "handle null user in create endpoint",
    ]),
    CommitGroup(category="test", messages=[
        "add route handler tests",
    ]),
]
```

**Why this matters**: Resume bullets like "Contributed 15 features and resolved 8 critical bugs" are quantifiable and specific. The breakdown enables LLMs to write: "Demonstrated feature delivery across authentication, API endpoints, and task management—while maintaining code quality through comprehensive test coverage." This is far more compelling than generic "built features."

**Test coverage**: 11 tests
- Conventional-commit prefixes (feat:, fix:, etc.) ✓
- Scopes in conventional commits ✓
- Keyword heuristics (add, fix, refactor, etc.) ✓
- Unclassifiable returns None ✓
- Full pipeline extracts & classifies ✓
- Groups have correct categories ✓
- Filters by user email ✓

---

### Structure Extractor

**File**: `extractors/structure.py`

**Purpose**: Identify which directories/modules the developer worked on.

**Algorithm**:
```
1. List all top-level directories (excluding .git, hidden dirs)
   Example: ["src", "tests", "docs", "scripts"]

2. Iterate through user's commits (up to 500)
   For each commit, extract file paths:
     Example: "src/api/routes.py", "src/models/user.py", "tests/test_auth.py"

3. Group files by top-level directory:
   {
     "src": ["src/api/routes.py", "src/models/user.py", ...],
     "tests": ["tests/test_auth.py", ...],
     "docs": ["docs/API.md"],
   }
```

**Output**:
```python
(
    ["src", "tests", "docs"],  # directory_overview
    {                           # module_groups
        "src": ["src/api/routes.py", "src/models/user.py"],
        "tests": ["tests/test_auth.py"],
    }
)
```

**Why this matters**: Knowing that a developer touched `src/api/`, `src/models/`, and `tests/` tells us they worked across API routes, data models, and testing. The LLM can then write "Contributed across API layer, data models, and comprehensive test coverage" rather than the generic "worked on various modules."

**Test coverage**: 3 tests
- Returns top-level directories ✓
- Excludes hidden directories ✓
- Groups user-touched files by module ✓

---

### Code Constructs Extractor

**File**: `extractors/constructs.py`

**Purpose**: Extract concrete code artifacts (routes, classes, tests, functions) to reference in bullets.

**Regex Patterns by Language**:

| Construct | Regex Pattern | Example |
|-----------|---------------|---------|
| Routes | `@(app\|router)\.get/post/put/delete\(\s*["']([^"']+)` | `GET /api/users` |
| Classes | `^\s*class\s+(\w+)` | `User`, `TaskService` |
| Tests | `def\s+(test_\w+)`, `it\(\s*["']` | `test_login`, `test_create_user` |
| Functions | `def\s+(\w+)\(`, `function\s+(\w+)` | `authenticate`, `serialize` |

**Language support**:
- Python: routes (FastAPI/Flask), classes, tests, functions
- JavaScript/TypeScript: routes (Express), classes, tests, functions
- Java: routes (Spring), classes, tests, functions
- Rust/Go: functions, structs, tests
- C#: classes, routes

**Filters**:
- Skip dunder methods (`__init__`, `__str__`, etc.)
- Skip test functions in the functions list (tracked separately)
- Skip private helpers (names starting with `_`)
- Skip trivial names (`main`, `run`, `setup`, `teardown`)

**Output**:
```python
CodeConstructs(
    routes=["GET /api/users", "POST /api/users", "DELETE /api/tasks/{id}"],
    classes=["User", "Task", "TaskService"],
    test_functions=["test_list_users", "test_create_user", "test_delete_task"],
    key_functions=["authenticate", "generate_token", "validate_input"],
)
```

**Why this matters**: Instead of LLM guessing at achievements, we give it concrete artifacts: "You found 3 API routes, 2 classes, 5 test functions, and 4 key service functions. Build bullets around these." The LLM then writes: "Implemented 3 user-facing API endpoints with comprehensive test coverage and modular service classes for maintainability."

**Test coverage**: 6 tests
- Finds FastAPI routes ✓
- Finds class definitions ✓
- Finds test function names ✓
- Finds key functions (non-test, non-dunder) ✓
- Scoped to touched files only ✓

---

### Project Type Inference

**File**: `extractors/project_type.py`

**Purpose**: Classify project as "Web API", "CLI Tool", "Library", etc., to frame contributions appropriately.

**Scoring System**:

```
Initialize scores = {}

For each indicator in INDICATORS:
    keyword, project_type, score

    if keyword found in:
        • frameworks list (FastAPI → +10 for "Web API")
        • README text (keyword "REST API" → +3 for "Web API")
        • directory names (api/ → +5 for "Web API", cli/ → +8 for "CLI Tool")
        • file names (setup.py → +4 for "Library")

    Then: scores[project_type] += score

Return: project_type with highest score
```

**Indicator Examples**:

| Keyword | Type | Score |
|---------|------|-------|
| FastAPI | Web API | 10 |
| Flask | Web API | 10 |
| Express | Web API | 10 |
| Typer | CLI Tool | 8 |
| Click | CLI Tool | 8 |
| setuptools | Library | 4 |
| tensorflow | ML/Data Pipeline | 8 |
| pytorch | ML/Data Pipeline | 8 |
| react | Web App | 6 |
| react-native | Mobile App | 10 |

**Examples**:

```
Input: frameworks=["FastAPI"], readme="REST API for task management"
Output: "Web API"
Score: FastAPI (+10) + "REST API" in README (+3) = 13

Input: frameworks=["Click"], directories=["cli/"]
Output: "CLI Tool"
Score: Click (+8) + cli/ directory (+4) = 12

Input: frameworks=["PyTorch"], readme="Deep learning model"
Output: "ML/Data Pipeline"
Score: PyTorch (+8) = 8
```

**Why this matters**: Framing matters. A developer's contributions to a "Web API" are described differently than a "Library":
- Web API: "Implemented 3 user-facing endpoints..."
- Library: "Designed public API with 4 core functions..."
- CLI Tool: "Built command-line interface with 8 subcommands..."

**Test coverage**: 4 tests
- Detects Web API from frameworks ✓
- Detects CLI Tool from frameworks ✓
- Fallback to generic type ✓
- README keywords boost scores ✓

---

## LLM Queries

### Prompt Design

Each prompt is designed for **small models (3B parameters)** with focused, structured output.

#### Project Prompt (`queries/prompts.py:build_project_prompt`)

**System Message**:
```
You are a professional resume writer for software engineers.
Rules:
- Be SPECIFIC: name actual features, endpoints, classes from the data.
- Use STRONG action verbs: Architected, Implemented, Designed, Engineered.
- EVERY bullet must trace to a commit message or code construct.
- NEVER invent features not present in the data.
- QUANTIFY when possible: contribution %, commit counts, number of endpoints.
- If the developer contributed >95%, use "Independently built" or "Architected".
```

**Prompt Structure**:
```
Using the project data below, write a resume section with EXACTLY this format:

DESCRIPTION: [1-2 sentences describing what this project is]
BULLETS:
- [achievement bullet 1]
- [achievement bullet 2]
- [achievement bullet 3]
NARRATIVE: [2-3 sentences about developer's specific contribution]

Rules:
- Description should explain what the project does (use README).
- Each BULLET must reference a concrete feature, endpoint, class, or fix.
- NARRATIVE should highlight the developer's role and technical decisions.
- Write 3-5 bullets depending on available data.
- If fewer than 3 commits, write fewer bullets—never fabricate.

[Full ProjectDataBundle context: README, routes, classes, commit messages, etc.]
```

**Input Example**:
```
PROJECT: my-web-api
Type: Web API
Stack: Python (72%), JavaScript (28%)
Frameworks: FastAPI, SQLAlchemy

Contribution: 100% (45/45 commits)
Period: 2024-01-15 to 2024-06-20

README excerpt:
A REST API for managing tasks and users built with FastAPI...

FEATURE commits (15):
  - implement user registration endpoint
  - add task CRUD operations
  - add JWT authentication
  ...

Routes: GET /api/users, POST /api/users, DELETE /api/tasks/{id}
Classes: User, Task, TaskService
Tests: test_list_users, test_create_user, test_delete_task
```

**Output Example**:
```
DESCRIPTION: A REST API for task management with JWT authentication and real-time updates.
BULLETS:
- Implemented 3 user endpoints (GET, POST, DELETE) with FastAPI decorators
- Built JWT token generation and validation helpers with cryptographic security
- Wrote 15+ unit tests covering all route handlers, model validation, and edge cases
- Designed modular service classes (User, Task, TaskService) for separation of concerns
NARRATIVE: Independently architected the entire backend, handling authentication, database models, API routes, and comprehensive test coverage with attention to type safety and error handling.
```

#### Portfolio Prompts

**Summary Prompt** (e.g., `build_summary_prompt`):
```
Write a 2-3 sentence professional summary for the top of a resume.

Portfolio:
- 5 projects
- 127 total commits
- Languages: Python, TypeScript, JavaScript
- Frameworks: FastAPI, SQLAlchemy, React, Vue
- Active period: 2024-01-15 to 2024-06-20

Projects: Web API (2), CLI Tool (1), Library (2)

Example: "Full-stack developer with 5 years building REST APIs and web applications..."
```

**Skills Prompt**:
```
Organize the following technologies into a clean skills section.

Languages: Python, TypeScript, JavaScript
Frameworks: FastAPI, SQLAlchemy, React, Vue
Skills: REST API Design, Authentication, Testing

Rules:
- Group into: Languages, Frameworks & Libraries, Infrastructure, Practices
- ONLY include items from the list above.
- Each item appears in EXACTLY ONE category.
- List names only, no descriptions or percentages.
```

**Profile Prompt**:
```
Write a 3-4 sentence developer profile paragraph.

Projects:
- my-web-api: 100% contribution, 15 features, 3 bugfixes, 2 tests
- my-cli-tool: 80% contribution, 8 features, 1 bugfix
- my-library: 100% contribution, 5 features, 2 bugfixes
...
```

---

## Output Formats

### Markdown Resume

```markdown
# Technical Resume

## Professional Summary
Full-stack developer with expertise building REST APIs and web applications across 5 projects in Python and TypeScript, focused on scalable systems and comprehensive testing.

## Technical Skills

Languages: Python, TypeScript, JavaScript
Frameworks & Libraries: FastAPI, SQLAlchemy, React, Vue
Infrastructure: PostgreSQL, Docker, GitHub Actions
Practices: Test-Driven Development, API Design, System Design

## Projects

### my-web-api
**Technologies:** FastAPI, SQLAlchemy | **Language:** Python | **Contribution:** 100%
**Period:** 2024-01-15 to 2024-06-20

A REST API for task management with JWT authentication and real-time updates.

- Implemented 3 user endpoints (GET, POST, DELETE) with FastAPI decorators
- Built JWT token generation and validation helpers with cryptographic security
- Wrote 15+ unit tests covering all route handlers, model validation, and edge cases
- Designed modular service classes (User, Task, TaskService) for separation of concerns

> Independently architected the entire backend, handling authentication, database models, API routes, and comprehensive test coverage with attention to type safety and error handling.

### my-cli-tool
**Technologies:** Typer, Click | **Language:** Python | **Contribution:** 80%
**Period:** 2024-02-20 to 2024-05-10

...

## Developer Profile
Demonstrates strong backend expertise with API design and comprehensive testing across all projects. Comfortable across the full stack (React, Vue, FastAPI, PostgreSQL). Shows growth from procedural scripts to modular service architectures, with consistent attention to type safety and developer experience.

---
*Generated with qwen2.5-coder-3b-q4 in 127.3s*
```

### JSON Resume

```json
{
  "professional_summary": "Full-stack developer with expertise...",
  "skills_section": "Languages: Python, TypeScript...",
  "developer_profile": "Demonstrates strong backend expertise...",
  "projects": [
    {
      "name": "my-web-api",
      "type": "Web API",
      "primary_language": "Python",
      "frameworks": ["FastAPI", "SQLAlchemy"],
      "contribution_pct": 100.0,
      "commit_breakdown": {
        "feature": 15,
        "bugfix": 3,
        "test": 2,
        "refactor": 1,
        "docs": 1,
        "chore": 22
      },
      "period": {
        "first_commit": "2024-01-15",
        "last_commit": "2024-06-20"
      },
      "description": "A REST API for task management with JWT authentication...",
      "bullets": [
        "Implemented 3 user endpoints (GET, POST, DELETE)...",
        "Built JWT token generation and validation helpers...",
        "Wrote 15+ unit tests covering all route handlers..."
      ],
      "narrative": "Independently architected the entire backend..."
    }
  ],
  "portfolio": {
    "total_projects": 5,
    "total_commits": 127,
    "languages_used": ["Python", "TypeScript", "JavaScript"],
    "frameworks_used": ["FastAPI", "SQLAlchemy", "React", "Vue"],
    "project_types": {
      "Web API": 2,
      "CLI Tool": 1,
      "Library": 2
    },
    "top_skills": ["REST API Design", "Authentication", "Testing", ...]
  },
  "metadata": {
    "model_used": "qwen2.5-coder-3b-q4",
    "generation_time_seconds": 127.3,
    "errors": []
  }
}
```

---

## Usage Guide

### CLI Command

```bash
# v3 pipeline (default)
uv run python -m artifactminer.resume generate \
  --zip /path/to/repos.zip \
  --email user@example.com \
  --model qwen2.5-coder-3b-q4 \
  --output-md resume.md \
  --output-json resume.json \
  --verbose

# v2 pipeline (legacy/rollback)
uv run python -m artifactminer.resume generate-v2 \
  --zip /path/to/repos.zip \
  --email user@example.com
```

### Programmatic Usage

```python
from artifactminer.resume import generate_resume_v3
from artifactminer.resume.assembler import assemble_markdown, assemble_json

result = generate_resume_v3(
    zip_path="/path/to/repos.zip",
    user_email="user@example.com",
    llm_model="qwen2.5-coder-3b-q4",
    progress_callback=lambda msg: print(msg),
)

markdown = assemble_markdown(result)
json_str = assemble_json(result)

print(markdown)
```

### Model Selection

| Model | Context | Speed | Quality | Use Case |
|-------|---------|-------|---------|----------|
| qwen2.5-coder-3b-q4 | 16K | Fast | Good | Default, code-focused |
| qwen3-1.7b-q8 | 32K | Medium | Good | Prose quality |
| deepseek-r1-qwen-1.5b-q8 | 32K | Slow | Excellent | Best quality (if time permits) |
| lfm2-2.6b-q8 | 20K | Fast | Good | Fast inference |

Default is `qwen2.5-coder-3b-q4` (smallest, fastest, adequate quality).

---

## Performance

### LLM Call Budget

| Phase | Calls | Model | Avg Time |
|-------|-------|-------|----------|
| Per-project queries | N (1 per project) | qwen2.5-coder-3b-q4 | ~10s each |
| Portfolio queries | 3 (summary, skills, profile) | qwen2.5-coder-3b-q4 | ~5s each |
| **Total** | **N + 3** | | **~10N + 15s** |

**Example (5 projects)**:
- Project queries: 5 × 10s = 50s
- Portfolio queries: 3 × 5s = 15s
- Overhead (extraction, assembly): ~30s
- **Total: ~95s**

**vs. v2 pipeline**: ~25 calls × 5s = 125s (25% slower)

### Extraction Time (without LLM)

If only running PHASE 1 (no LLM server needed):
```
5 projects × 10 extractors per project = 50 total extractions

README extraction: 50 × 10ms = 500ms
Commit extraction: 50 × 50ms = 2.5s
Structure extraction: 50 × 100ms = 5s
Constructs extraction: 50 × 50ms = 2.5s
Project type inference: 50 × 5ms = 250ms

Total: ~11s (no LLM required)
```

### Test Coverage

```
tests/resume/test_extractors.py        29 tests  ✓ 3.5s
tests/resume/test_prompts.py          16 tests  ✓ 2.1s
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Total                                 45 tests  ✓ 5.6s
```

All tests run without LLM server or network access.

---

## Troubleshooting

### Model Not Found

```
Error: Model 'qwen2.5-coder-3b-q4' is not available.
```

**Fix**:
```bash
uv run python -m artifactminer.resume download-model qwen2.5-coder-3b-q4
```

### Empty Resume Output

**Common causes**:
1. ZIP file contains no git repositories
2. User email doesn't match any commits
3. LLM model failed (check --verbose output)

**Debug**:
```bash
uv run python -m artifactminer.resume generate \
  --zip /path/to/repos.zip \
  --email user@example.com \
  --verbose  # Shows all extraction steps
```

### llama-server Port Conflicts

If multiple sessions run simultaneously:
```
Error: llama-server port already in use
```

The system automatically selects a free port, but if you have stale llama-server processes:
```bash
pkill llama-server
```

---

## Future Enhancements

1. **Hybrid extraction**: Combine commit classification with code metrics (cyclomatic complexity, test coverage %)
2. **Multi-model pipelines**: Use qwen2.5-coder-3b for extraction, deepseek-r1 for narrative generation
3. **Interactive refinement**: Let users adjust project descriptions, bullets, and skills before final assembly
4. **Skill timeline narratives**: Generate "Adopted TypeScript in March 2024..." from `ProjectDataBundle.skill_first_appearances`
5. **Code style fingerprinting**: Narrative like "Writes concise, well-tested functions (avg 12 lines, 85% test coverage)"

---

## Related Documentation

- [Resume v3 Guide](./RESUME_V3_GUIDE.md) — Step-by-step usage examples
- [API Specification](./API.md) — LLM prompt formats and response schemas
- Source code: `src/artifactminer/resume/`
