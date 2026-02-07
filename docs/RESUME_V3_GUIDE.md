# Resume v3 — Practical Usage Guide

This guide shows how to use the v3 resume pipeline with real examples.

---

## Quick Start

### 1. Prepare Your ZIP File

Your ZIP should contain git repositories. Example structure:

```
repos.zip
├── my-web-api/
│   ├── .git/
│   ├── README.md
│   ├── src/
│   │   ├── api/
│   │   ├── models/
│   │   └── auth.py
│   └── tests/
├── my-cli-tool/
│   ├── .git/
│   ├── README.md
│   └── cli/
├── data-pipeline/
│   ├── .git/
│   └── notebooks/
```

### 2. Run Generation

```bash
uv run python -m artifactminer.resume generate \
  --zip /path/to/repos.zip \
  --email your@email.com \
  --output-md resume.md \
  --output-json resume.json \
  --verbose
```

### 3. Review Output

```bash
# View markdown in terminal
cat resume.md

# View JSON (useful for frontend)
cat resume.json | jq .
```

---

## Detailed Walkthrough

### Step 1: Download Model (First Time Only)

```bash
# Check available models
uv run python -m artifactminer.resume check-models

# Download the default model
uv run python -m artifactminer.resume download-model qwen2.5-coder-3b-q4

# Or another model
uv run python -m artifactminer.resume download-model qwen3-1.7b-q8
```

Output:
```
Installed models:
  - qwen2.5-coder-3b-q4
  - qwen3-1.7b-q8

Model directory: /Users/yourname/.artifactminer/models/

Downloadable models (8):
  - qwen2.5-coder-3b-q4 (installed) — Qwen/Qwen2.5-Coder-3B-Instruct-GGUF
  - qwen3-1.7b-q8 (not installed) — unsloth/Qwen3-1.7B-Instruct-GGUF
  ...
```

### Step 2: Run Generation with Progress

```bash
uv run python -m artifactminer.resume generate \
  --zip ~/Downloads/repos.zip \
  --email john@example.com \
  --model qwen2.5-coder-3b-q4 \
  --output-md resume.md \
  --verbose
```

Output:
```
[resume] Ensuring model 'qwen2.5-coder-3b-q4' is available...
[resume] Extracting ~/Downloads/repos.zip...
[resume] Extracted to /tmp/repos_extracted
[resume] Discovering git repositories...
[resume] Found 3 repositories
[resume] Analyzing [1/3]: my-web-api
  Extracting README...
  Classifying commits...
  Extracting structure...
  Extracting code constructs...
  Inferring project type...
  Done: Web API, 45 commits, 8 skills, 3 routes
[resume] Analyzing [2/3]: my-cli-tool
  Done: CLI Tool, 23 commits, 5 skills, 0 routes
[resume] Analyzing [3/3]: data-pipeline
  Done: ML/Data Pipeline, 67 commits, 6 skills, 0 routes
[resume] Portfolio: 3 projects, 18 skills, 3 languages
[resume] Querying LLM for my-web-api...
[resume] Querying LLM for my-cli-tool...
[resume] Querying LLM for data-pipeline...
[resume] Generating professional summary...
[resume] Generating skills section...
[resume] Generating developer profile...
[resume] Generation complete in 127.3s

============================================================
# Technical Resume
...
============================================================
GENERATION SUMMARY (v3)
============================================================
Projects analyzed: 3
Total commits: 135
Skills detected: 18
Project types: {'Web API': 1, 'CLI Tool': 1, 'ML/Data Pipeline': 1}
Model used: qwen2.5-coder-3b-q4
Generation time: 127.3s

Markdown output written to: resume.md
JSON output written to: resume.json
```

### Step 3: Review the Generated Resume

```markdown
# Technical Resume

## Professional Summary
Full-stack developer with 5 years building REST APIs, command-line tools, and data pipelines in Python and TypeScript. Skilled in API design, data processing, and test-driven development across diverse project types.

## Technical Skills

Languages: Python, TypeScript, JavaScript
Frameworks & Libraries: FastAPI, SQLAlchemy, Typer, Click, Pandas, PyTorch
Infrastructure: PostgreSQL, Docker, GitHub Actions, Jupyter
Practices: Test-Driven Development, API Design, Data Pipeline Architecture

## Projects

### my-web-api
**Technologies:** FastAPI, SQLAlchemy | **Language:** Python | **Contribution:** 100%
**Period:** 2024-01-15 to 2024-06-20

A REST API for task management with real-time updates and JWT authentication.

- Implemented 3 user-facing endpoints (GET, POST, DELETE) with FastAPI decorators
- Built JWT token generation and validation with cryptographic security
- Wrote 20+ unit tests covering all route handlers, model validation, and edge cases
- Designed modular service classes (User, Task, TaskService) for maintainability

> Independently architected the entire backend, handling authentication, database models, comprehensive test coverage, and type safety. Made key decisions around async request handling and database connection pooling.

### my-cli-tool
**Technologies:** Typer, Click | **Language:** Python | **Contribution:** 80%
**Period:** 2024-02-20 to 2024-05-10

A command-line data processing tool for ETL workflows with interactive mode.

- Implemented 5 subcommands (extract, transform, load, validate, schedule) using Typer decorators
- Built interactive REPL mode for exploratory data analysis
- Created 8 data validation schemas using Pydantic for type safety
- Wrote comprehensive documentation with examples and configuration guide

> Primary contributor to CLI design and implementation. Collaborated with data team to validate pipeline requirements. Added interactive features that reduced manual data entry by 60%.

### data-pipeline
**Technologies:** Pandas, PyTorch | **Language:** Python | **Contribution:** 60%
**Period:** 2024-03-01 to 2024-07-15

Machine learning pipeline for sentiment analysis with scalable inference.

- Developed ETL pipeline processing 100K documents daily using Pandas and custom scripts
- Implemented PyTorch model inference with batch processing for 10x throughput improvement
- Created monitoring dashboard tracking model accuracy and data quality metrics
- Contributed 15 features and 8 bug fixes to core pipeline infrastructure

> Collaborated with ML team on infrastructure and data quality. Focused on scalability and monitoring. Demonstrated ownership of critical data pipeline components.

## Developer Profile
Shows strong backend engineering skills with consistent test coverage and clean architecture patterns across all projects. Comfortable across the full stack (frontend, APIs, databases, ML infrastructure). Demonstrates growth from procedural scripts to modular, production-ready systems. Values code quality, testing, and collaboration.

---
*Generated with qwen2.5-coder-3b-q4 in 127.3s*
```

---

## Extracting Individual Components

### Get Just the Data (No Markdown)

```python
from artifactminer.resume import generate_resume_v3

result = generate_resume_v3(
    zip_path="/path/to/repos.zip",
    user_email="john@example.com",
)

# Portfolio data (aggregated)
portfolio = result.portfolio_data
print(f"Total projects: {portfolio.total_projects}")
print(f"Top skills: {portfolio.top_skills}")
print(f"Languages: {portfolio.languages_used}")
print(f"Date range: {portfolio.earliest_commit} to {portfolio.latest_commit}")

# Per-project data
for project in portfolio.projects:
    print(f"\n{project.project_name} ({project.project_type})")
    print(f"  Contribution: {project.user_contribution_pct:.0f}%")
    print(f"  Commits: {project.user_total_commits}")
    print(f"  Frameworks: {', '.join(project.frameworks)}")
    print(f"  Skills: {', '.join(project.detected_skills[:5])}")

# Generated sections
print(f"\nSummary: {result.professional_summary}")
print(f"Skills:\n{result.skills_section}")
for proj_name, section in result.project_sections.items():
    print(f"\n{proj_name}:")
    print(f"  Bullets: {section.bullets}")
```

### Custom Formatting

```python
from artifactminer.resume import generate_resume_v3
from artifactminer.resume.assembler import assemble_json
import json

result = generate_resume_v3(
    zip_path="/path/to/repos.zip",
    user_email="john@example.com",
)

# Get JSON data
json_str = assemble_json(result)
data = json.loads(json_str)

# Custom formatting — e.g., CSV of projects
for project in data["projects"]:
    print(f"{project['name']},{project['type']},{project['primary_language']},{project['contribution_pct']}")
```

---

## Understanding the Extraction Process

### What Gets Extracted from Each Project

When you run the pipeline on a single repository, here's what happens:

#### README Extraction
```
Input: /path/to/repo/README.md
↓
Reads up to 2000 characters (exact)
↓
Output: "# My Web API
A REST API for managing tasks..."
```

**Used for**: Project description context in LLM prompt

---

#### Commit Classification
```
Input: Git history for user@email.com
↓
Step 1: Static Classification
  ├─ "feat: add user registration" → feature (conventional prefix)
  ├─ "Implement task CRUD" → feature (keyword heuristic)
  ├─ "Fix null pointer" → bugfix (keyword heuristic)
  └─ "Unknown message" → UNCLASSIFIED

Step 2: LLM Fallback (if enabled)
  └─ Send unclassified to LLM → 100% coverage

Step 3: Default (if no LLM)
  └─ Unclassified → "feature"
↓
Output: CommitGroup(
    category="feature",
    messages=["add user registration", "Implement task CRUD"]
)
```

**Used for**: Commit breakdown in bullets ("Contributed 15 features and 3 bug fixes")

---

#### Structure Extraction
```
Input: Repository directory + git history
↓
Step 1: Top-level directories
  └─ "src", "tests", "docs", "scripts"

Step 2: For each user commit, collect file paths
  ├─ Commit 1: "src/api/routes.py", "src/models/user.py"
  ├─ Commit 2: "tests/test_auth.py"
  └─ Commit 3: "src/api/routes.py" (already seen, skip)

Step 3: Group by top-level directory
  ├─ src: ["src/api/routes.py", "src/models/user.py"]
  └─ tests: ["tests/test_auth.py"]
↓
Output: (
    ["src", "tests", "docs"],  # directory_overview
    {                           # module_groups
        "src": [...],
        "tests": [...]
    }
)
```

**Used for**: Module context ("Contributed across API layer, data models, and tests")

---

#### Code Constructs Extraction
```
Input: Repository files (those user touched)
↓
Step 1: Scan Python/JS/TS/Java/etc. files with regex
  ├─ Routes: @app.get(), @router.post(), etc.
  │   └─ Found: "GET /api/users", "POST /api/users"
  ├─ Classes: class ClassName:
  │   └─ Found: "User", "TaskService"
  ├─ Tests: def test_xxx():
  │   └─ Found: "test_create_user", "test_delete_task"
  └─ Functions: def function_name():
      └─ Found: "authenticate", "generate_token"

Step 2: Filter out noise
  ├─ Skip dunder methods (__init__, __str__)
  ├─ Skip private helpers (_internal_function)
  └─ Skip trivial names (main, run, setup)
↓
Output: CodeConstructs(
    routes=["GET /api/users", "POST /api/users"],
    classes=["User", "TaskService"],
    test_functions=["test_create_user", "test_delete_task"],
    key_functions=["authenticate", "generate_token"]
)
```

**Used for**: Concrete features in bullets ("Implemented user registration endpoint with validation and error handling")

---

#### Project Type Inference
```
Input: Frameworks + README + directory names
↓
Scoring:
  ├─ FastAPI framework found → +10 for "Web API"
  ├─ "REST API" in README → +3 for "Web API"
  ├─ "api/" directory exists → +5 for "Web API"
  └─ Total score for "Web API": 18 (highest)
↓
Output: "Web API"
```

**Used for**: Framing ("Architected a REST API..." vs "Built a CLI tool..." vs "Designed a library API...")

---

### Complete Data Bundle Example

Here's what a full `ProjectDataBundle` looks like after extraction:

```python
ProjectDataBundle(
    project_name="my-web-api",
    project_path="/tmp/repos/my-web-api",
    project_type="Web API",

    # Tech stack
    languages=["Python", "JavaScript"],
    language_percentages=[72.0, 28.0],
    primary_language="Python",
    frameworks=["FastAPI", "SQLAlchemy"],

    # Contribution
    user_contribution_pct=100.0,
    user_total_commits=45,
    total_commits=45,
    first_commit="2024-01-15T08:30:00",
    last_commit="2024-06-20T16:45:00",

    # README
    readme_text="# My Web API\n\nA REST API for managing tasks and users...",

    # Commits (from hybrid classifier)
    commit_groups=[
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
    ],

    # Structure
    directory_overview=["src", "tests", "docs"],
    module_groups={
        "src": ["src/api/routes.py", "src/models/user.py"],
        "tests": ["tests/test_routes.py"],
    },

    # Code constructs
    constructs=CodeConstructs(
        routes=["GET /api/users", "POST /api/users", "DELETE /api/tasks/{id}"],
        classes=["User", "Task", "TaskService"],
        test_functions=["test_list_users", "test_create_user"],
        key_functions=["authenticate", "serialize"],
    ),

    # From existing analyzers
    detected_skills=["REST API Design", "Authentication"],
    skill_evidence={
        "REST API Design": ["@router.get in api/routes.py"],
        "Authentication": ["JWT token generation"],
    },
    insights=[
        {
            "title": "API Design",
            "why": "RESTful endpoints with proper HTTP methods",
            "evidence": ["GET /api/users", "POST /api/users"],
        },
    ],
)
```

---

## LLM Query Examples

### What Gets Sent to the LLM

For the bundle above, here's the exact prompt sent to the LLM:

```
You are a professional resume writer for software engineers.
Rules:
- Be SPECIFIC: name actual features, endpoints, classes from the data.
- Use STRONG action verbs: Architected, Implemented, Designed.
- EVERY bullet must trace to a commit message or code construct.
- NEVER invent features not present in the data.
...

This is a SOLO project (the developer wrote nearly all the code).
Use phrases like 'Independently built', 'Architected and implemented', etc.

Using the project data below, write a resume section with EXACTLY this format:

DESCRIPTION: [1-2 sentences describing what this project is and does]
BULLETS:
- [achievement bullet 1]
- [achievement bullet 2]
- [achievement bullet 3]
NARRATIVE: [2-3 sentences about the developer's specific contribution and impact]

PROJECT: my-web-api
Type: Web API
Stack: Python (72%), JavaScript (28%)
Frameworks: FastAPI, SQLAlchemy

Contribution: 100% (45/45 commits)
Period: 2024-01-15 to 2024-06-20

README excerpt:
# My Web API

A REST API for managing tasks and users built with FastAPI...

FEATURE commits (3):
  - implement user registration endpoint
  - add task CRUD operations
  - add JWT authentication

BUGFIX commits (1):
  - handle null user in create endpoint

TEST commits (1):
  - add route handler tests

Routes: GET /api/users, POST /api/users, DELETE /api/tasks/{id}
Classes: User, Task, TaskService
Tests: test_list_users, test_create_user
Key functions: authenticate, serialize

Modules worked on:
  src/ (2 files)
  tests/ (1 file)
```

### LLM Response

The model outputs:

```
DESCRIPTION: A REST API for task management with JWT authentication and real-time updates built with FastAPI.
BULLETS:
- Implemented 3 user endpoints (GET, POST, DELETE) with FastAPI decorators and type validation
- Built JWT token generation and validation helpers with cryptographic security
- Wrote comprehensive unit tests covering all route handlers, model validation, and edge cases
NARRATIVE: Independently architected the entire backend, handling authentication, database models, API routes, and comprehensive test coverage with attention to type safety and error handling.
```

This response gets parsed into:
```python
ProjectSection(
    description="A REST API for task management with JWT authentication...",
    bullets=[
        "Implemented 3 user endpoints (GET, POST, DELETE)...",
        "Built JWT token generation and validation helpers...",
        "Wrote comprehensive unit tests...",
    ],
    narrative="Independently architected the entire backend...",
)
```

---

## Model Comparison

Different models produce different quality outputs. Here's what you get with each:

### qwen2.5-coder-3b-q4 (DEFAULT)
- **Speed**: ~10s per project
- **Quality**: Good, code-focused
- **Size**: 3B parameters
- **Best for**: Default choice, fast iteration

Output style:
> "Implemented 3 user endpoints (GET, POST, DELETE) with FastAPI decorators. Built JWT authentication with token validation. Wrote 15+ unit tests covering all handlers."

### qwen3-1.7b-q8
- **Speed**: ~12s per project
- **Quality**: Good, balanced prose
- **Size**: 1.7B parameters
- **Best for**: Smaller model, still decent quality

Output style:
> "Architected a REST API with 3 user-facing endpoints and comprehensive JWT authentication. Demonstrated strong testing practices with 15+ unit tests ensuring robust error handling and type safety."

### deepseek-r1-qwen-1.5b-q8
- **Speed**: ~20s per project (includes reasoning)
- **Quality**: Excellent, thoughtful prose
- **Size**: 1.5B parameters (with reasoning)
- **Best for**: Best quality if you have time

Output style:
> "Independently architected the entire REST API backend, demonstrating expertise across multiple dimensions: implemented 3 RESTful endpoints with proper HTTP semantics, designed JWT authentication with cryptographic security, and established comprehensive test coverage. The architectural decisions—modular service classes and type validation—reflect professional-grade engineering practices."

---

## Troubleshooting Common Issues

### Issue: "No git repositories found in ZIP"

**Cause**: ZIP doesn't contain `.git` directories, or they're nested too deep.

**Solution**:
```bash
# Check what's in the ZIP
unzip -l /path/to/repos.zip | head -20

# The ZIP should have this structure:
# repo-name/
#   .git/        ← MUST exist for discovery
#   .gitignore
#   README.md
#   src/
#   ...
```

---

### Issue: "User email doesn't match any commits"

**Cause**: Git author email in the repo doesn't match the email you provided.

**Solution**:
```bash
# Check what email is in the repo
cd /tmp/repo
git log --pretty=format:"%ae" | sort | uniq

# Use the email found in the repo
uv run python -m artifactminer.resume generate \
  --zip repos.zip \
  --email correct.email@example.com  # Use exact match from above
```

---

### Issue: LLM queries returning empty responses

**Cause**: Model doesn't support structured JSON output, or context window was exceeded.

**Solution**:
```bash
# Try a different model
uv run python -m artifactminer.resume generate \
  --zip repos.zip \
  --email user@example.com \
  --model qwen3-1.7b-q8  # Try a different one
```

---

### Issue: Generation takes >10 minutes

**Cause**:
1. Large ZIP with many projects
2. Large repositories with many commits to process
3. Using a slow model (deepseek-r1-qwen-1.5b)

**Solution**:
```bash
# Use faster model
uv run python -m artifactminer.resume generate \
  --zip repos.zip \
  --email user@example.com \
  --model qwen2.5-coder-3b-q4  # Fastest option
```

---

## Next Steps

1. **Customize project types**: Edit `src/artifactminer/resume/extractors/project_type.py` to add custom scoring rules
2. **Adjust LLM prompts**: Edit `src/artifactminer/resume/queries/prompts.py` to change tone/style
3. **Post-process output**: Parse the JSON resume and format it however you want (PDF, HTML, ATS-friendly plain text)

---

## Advanced: Running Tests

```bash
# Run all resume tests
uv run pytest tests/resume/ -v

# Run extractors only
uv run pytest tests/resume/test_extractors.py -v

# Run prompts/assembly only
uv run pytest tests/resume/test_prompts.py -v

# Run with coverage
uv run pytest tests/resume/ --cov=artifactminer.resume
```

Expected output:
```
tests/resume/test_extractors.py::TestExtractReadme::test_extracts_readme_content PASSED
tests/resume/test_extractors.py::TestClassifyStatic::test_conventional_feat PASSED
...
45 passed in 5.6s
```

---

## Integration: Using Resume Data in Your Application

```python
from artifactminer.resume import generate_resume_v3
from artifactminer.resume.assembler import assemble_json
import json

def generate_portfolio_resume(zip_path: str, email: str) -> dict:
    """Generate resume and return structured data for frontend."""
    result = generate_resume_v3(
        zip_path=zip_path,
        user_email=email,
        llm_model="qwen2.5-coder-3b-q4",
    )
    return json.loads(assemble_json(result))

# Usage in FastAPI
from fastapi import FastAPI

app = FastAPI()

@app.post("/generate-resume")
def create_resume(zip_path: str, email: str):
    resume_data = generate_portfolio_resume(zip_path, email)
    return resume_data

# Caller gets JSON-serialized resume with:
# - professional_summary
# - skills_section
# - projects (with description, bullets, narrative)
# - developer_profile
# - metadata (model used, generation time)
```

---

**For detailed architecture info**, see [RESUME_V3_PIPELINE.md](./RESUME_V3_PIPELINE.md).
