# Local LLM Research: Resume-Quality Artifact Generation

> **Goal:** Use a local LLM to generate resume-worthy project summaries and portfolio profiles from a user's git contributions. Not just proficiency scores - real narrative artifacts.
>
> **Constraints:**
> - Default: fully local/offline (no cloud APIs)
> - Optional: cloud APIs (OpenAI etc.) if user consents and provides an API key
> - Target: MacBook Air M2 with 8GB total RAM (minimum)
> - User chooses model size (2B-8B tiers)
> - Speed is NOT a priority. 10+ minutes is acceptable for stellar output.
>
> **Date:** February 2026

---

## Table of Contents

1. [What We're Building](#what-were-building)
2. [Approaches Evaluated](#approaches-evaluated)
3. [Recommended Architecture: Multi-Pass Pipeline](#recommended-architecture-multi-pass-pipeline)
4. [LLM Model Selection](#llm-model-selection)
5. [Resume Generation: What Makes Great Output](#resume-generation-what-makes-great-output)
6. [Prompt Engineering](#prompt-engineering)
7. [RAM Budget and Model Tiers](#ram-budget-and-model-tiers)
8. [Relationship to Existing System](#relationship-to-existing-system)
9. [Open Questions](#open-questions)
10. [Appendix: Full Model Comparison](#appendix-full-model-comparison)
11. [Appendix: Approaches That Don't Work](#appendix-approaches-that-dont-work)

---

## What We're Building

### The Output

For **each repository**, generate:
- A rich narrative project summary (what the user built, what technologies they used, what architectural decisions they made)
- Resume-ready bullet points following the formula: **"[Action verb] [what] using [technologies] resulting in [impact]"**
- Key technical highlights and achievements

For the **entire portfolio**, generate:
- A unified profile that synthesizes skills across ALL repos
- Skill progression story (e.g., "Started with Flask, progressed to FastAPI with async middleware")
- A cohesive narrative the user could paste into a resume or portfolio site

### What This Is NOT

- NOT just proficiency scores (the arbitrary 0-1 numbers)
- NOT a replacement for Evan's existing summary generation (runs alongside it)
- NOT dependent on cloud APIs (works fully offline by default)

---

## Approaches Evaluated

We evaluated 6 approaches. Here's the honest verdict on each:

### 1. Agentic (OpenCode/Aider + Local LLM) - DOES NOT WORK

**Why:** 2-4B models cannot function as agents. Period.

- OpenCode is not an SDK - it's an end-user app
- Aider IS embeddable in Python but warns: "Models weaker than GPT-3.5 may have problems"
- Zero models under 7B have ever been benchmarked on any agent leaderboard (BFCL, SWE-Bench, Aider)
- Agent overhead: 3,000-10,000 tokens per step. With 32K context = max 5-7 steps before context exhaustion
- Latency: 2-40 minutes for a 5-step workflow on M2

**Verdict:** Eliminated.

### 2. RAG (Vector DB + Local LLM) - OVERKILL FOR THIS USE CASE

**Why:** We already have scoped data. RAG solves a problem we don't have.

- RAG shines when you need to find relevant needles in massive haystacks
- Our input is already scoped: one user's git additions, already processed by regex
- The vector DB retrieval step adds complexity without clear benefit
- 4.4x more tokens than the post-processing approach

**Where RAG WOULD make sense:** If we were querying across hundreds of repos or building a persistent skill database. Not for per-repo analysis.

**Verdict:** Not the right tool for this specific job.

### 3. Post-Processing (LLM Refines Regex Scores) - GOOD BUT TOO NARROW

**Why:** We don't actually want better scores. We want narratives.

- Research confirms 2-4B models CAN refine scores effectively
- Token-efficient (~2,200 tokens per evaluation)
- But the user said: "we don't care about scores, the numbers are arbitrary"
- This approach improves the wrong thing

**Verdict:** Solves a problem we no longer care about.

### 4. Multi-Pass Pipeline (Map-Reduce) - THE WINNER

**Why:** This is the only approach that can process large codebases AND generate rich narratives with small models.

- Split the work across multiple focused LLM calls
- Each call has a small, manageable context
- Hierarchical summarization: files → project → portfolio
- Works within 32K context limits
- Can take 10+ minutes (which is fine)

**Verdict:** Recommended. Details below.

### 5. Tree-sitter + LLM - VALUABLE ENHANCEMENT TO #4

**Why:** Reduces token usage by 40-60% by sending structured features instead of raw code.

- Parse code into AST, extract structural features
- Feed compact JSON summary to LLM instead of raw code
- 50-100 tokens per file vs 200-400 for raw code
- Supports 40+ languages via tree-sitter

**Verdict:** Use as an enhancement within the multi-pass pipeline.

### 6. Embedding Similarity (No LLM) - TOO WEAK FOR NARRATIVES

**Why:** Can detect skills but cannot generate text.

- Good for fast skill detection (40-60ms)
- Cannot produce project summaries or resume bullets
- Moderate accuracy (70-80%)

**Verdict:** Could be a fast pre-filter, but not the core solution.

---

## Recommended Architecture: Multi-Pass Pipeline

### Overview

Since speed doesn't matter and quality is everything, we use multiple sequential LLM calls, each with a focused task and manageable context.

```
PASS 1: DISCOVERY
"What files matter?"
  Input:  File manifest (names, sizes, languages, imports)
  Output: Ranked list of the most important files
  Tokens: ~1,000-2,000 in, ~500 out

          ↓

PASS 2: FILE ANALYSIS (one call per important file)
"What did the user build in this file?"
  Input:  User's code additions for ONE file
  Output: Structured summary of that file
  Tokens: ~1,000-3,000 in, ~500 out
  Repeat: For each important file (5-20 files)

          ↓

PASS 3: PROJECT SYNTHESIS
"What's the story of this project?"
  Input:  All file summaries from Pass 2
  Output: Rich project narrative + resume bullets
  Tokens: ~2,000-4,000 in, ~1,000 out

          ↓

PASS 4: PORTFOLIO SYNTHESIS (after all repos processed)
"What's the user's overall profile?"
  Input:  All project summaries from Pass 3
  Output: Unified portfolio profile + skill progression
  Tokens: ~2,000-5,000 in, ~1,500 out
```

### Pass 1: Discovery

**Goal:** Given a list of all files the user touched, figure out which ones are most important to analyze.

**Input format:**
```
Files touched by user in repo "my-api-project":

1. src/api/routes.py          (245 lines, imports: fastapi, sqlalchemy)
2. src/api/middleware.py       (89 lines, imports: fastapi, logging)
3. src/models/user.py          (156 lines, imports: sqlalchemy, pydantic)
4. src/utils/helpers.py        (42 lines, imports: os, pathlib)
5. tests/test_routes.py        (312 lines, imports: pytest, httpx)
6. requirements.txt            (15 lines)
7. README.md                   (78 lines)
8. .github/workflows/ci.yml   (45 lines)
...
```

**What we ask the LLM:**
- Pick the 5-10 most important files for understanding what this developer built
- Rank by: core application logic > tests > configuration > documentation

**Why a small model can handle this:**
- This is essentially a ranking/classification task
- Input is structured and small (~1,000 tokens)
- Clear criteria provided in prompt
- Fallback: if LLM fails, rank by file size + recency (heuristic)

### Pass 2: File Analysis

**Goal:** For each important file, summarize what the user built.

**Input:** The user's ACTUAL code additions for that file (extracted from git diff). If the file is very large (>2,000 tokens), use tree-sitter to extract structural features instead.

**What we ask the LLM:**
- What does this code do?
- What technologies/patterns does it use?
- What's the complexity level? (beginner/intermediate/advanced)
- What's the most impressive thing in this file?

**Output format (structured JSON):**
```json
{
  "file": "src/api/routes.py",
  "purpose": "REST API endpoints for user management",
  "technologies": ["FastAPI", "SQLAlchemy", "Pydantic"],
  "patterns": ["async/await", "dependency injection", "data validation"],
  "complexity": "intermediate",
  "highlights": [
    "Implements CRUD operations with proper error handling",
    "Uses Depends() for database session management"
  ]
}
```

**Why this works with small models:**
- Each call sees only ONE file (manageable context)
- Structured output format is easier for small models
- Code is already scoped to the user's additions only

**Tree-sitter optimization:** For files over 2,000 tokens, parse with tree-sitter first and send a structural summary instead of raw code. This reduces tokens by 40-60%.

### Pass 3: Project Synthesis

**Goal:** Combine all file summaries into a cohesive project narrative.

**Input:** All JSON summaries from Pass 2 (typically 1,000-3,000 tokens total).

**What we ask the LLM:**
- Write a project summary suitable for a resume/portfolio
- Generate 3-5 bullet points following "Built X using Y resulting in Z"
- Identify the user's strongest contributions
- Note any architectural decisions worth highlighting

**Output:**
```
PROJECT: my-api-project

Summary:
Built a RESTful API for user management using FastAPI and SQLAlchemy,
featuring async database operations, JWT authentication, and comprehensive
input validation with Pydantic models.

Resume Bullets:
- Architected RESTful API with 15+ endpoints using FastAPI and SQLAlchemy,
  implementing async database operations for improved throughput
- Designed data validation layer using Pydantic models with custom validators,
  ensuring type-safe request/response handling across all endpoints
- Implemented CI/CD pipeline with GitHub Actions including automated testing
  with 85% code coverage via pytest

Key Technologies: Python, FastAPI, SQLAlchemy, Pydantic, pytest, Docker
```

### Pass 4: Portfolio Synthesis

**Goal:** The LLM receives ALL project summaries and writes a unified profile.

**Input:** Project summaries from Pass 3 across all repos.

**What we ask the LLM:**
- Synthesize a portfolio-wide developer profile
- Show skill progression across projects
- Identify strongest areas and breadth of experience
- Generate a "Summary" section suitable for the top of a resume

**Output:**
```
DEVELOPER PROFILE

Summary:
Full-stack developer with demonstrated experience building production-grade
Python APIs and data pipelines. Progressed from basic Flask applications to
advanced FastAPI services with async operations, showing consistent growth
in API design, database architecture, and DevOps practices.

Skill Progression:
- Backend: Flask (basic) → FastAPI (advanced) with async patterns
- Data: pandas (intermediate) → SQLAlchemy ORM (advanced)
- Testing: unittest → pytest with fixtures and parametrization
- DevOps: Manual deployment → Docker + GitHub Actions CI/CD

Strongest Areas:
1. API Design & Architecture (demonstrated across 3 projects)
2. Data Modeling & Validation (Pydantic, SQLAlchemy)
3. Asynchronous Programming (async/await patterns throughout)
```

### Error Handling and Fallbacks

At every pass, if the LLM fails (timeout, garbled output, JSON parse error):

```
Pass 1 fallback: Rank files by (line count * recency) heuristic
Pass 2 fallback: Use tree-sitter structural extraction only (no narrative)
Pass 3 fallback: Template-based summary from file metadata
Pass 4 fallback: Concatenate project summaries with section headers
```

The system ALWAYS produces output, even if the LLM is unavailable.

---

## LLM Model Selection

### User-Selectable Tiers

Since the user chooses their model size based on their machine:

| Tier | Model | Params | Q4 RAM | Quality | Speed | Min Machine RAM |
|------|-------|--------|--------|---------|-------|-----------------|
| **Small** | Qwen3-1.7B or DS-R1-Distill-1.5B | 1.5-1.7B | ~1.5 GB | Decent | Fast | 8 GB |
| **Medium** | Phi-4-mini or Qwen2.5-Coder-3B | 3-3.8B | ~2.5 GB | Good | Moderate | 8 GB |
| **Large** | Qwen3-4B or Gemma 3 4B | 4B | ~3 GB | Better | Moderate | 8-16 GB |
| **XL** | Qwen2.5-Coder-7B or Llama 3.1 8B | 7-8B | ~5 GB | Best | Slow | 16 GB |
| **Cloud** | GPT-4o / Claude (via API key) | N/A | 0 GB | Excellent | Fast | Any |

### Recommended Default: Phi-4-mini (3.8B)

**Why:**
- Highest code benchmark in sub-4B class (62.8% HumanEval)
- Native JSON/function calling support
- 128K context window
- MIT license (no restrictions)
- ~2.5 GB at Q4 - fits comfortably on 8GB machine
- Available via Ollama: `ollama pull phi4-mini`

### For the XL Tier: Qwen2.5-Coder-7B

**Why:**
- Purpose-built for code (5.5T code tokens in training)
- Dramatically better generation quality than sub-4B models
- Will be slow on 8GB machine but user said they don't care about speed
- Available via Ollama: `ollama pull qwen2.5-coder:7b`

### For Cloud Tier

Use the existing consent system. If user provides an OpenAI/Claude API key, route all LLM calls through that API instead of Ollama. Quality will be dramatically better.

---

## Resume Generation: What Makes Great Output

### The Golden Formula

From resume research (Laszlo Bock, former Google SVP):

**"Accomplished [X] as measured by [Y] by doing [Z]"**

Examples:
- "Reduced API response time **by 60%** by implementing Redis caching layer with FastAPI dependency injection"
- "Architected data pipeline processing **10K+ records daily** using pandas and SQLAlchemy with automated error recovery"

### What We Can Extract from Code

| Code Signal | Resume Content |
|-------------|---------------|
| Languages/frameworks in imports | Technologies section |
| Number of endpoints/functions | Scale indicator ("15+ endpoints") |
| Test files present | Quality practice ("comprehensive test suite") |
| Async patterns | Architecture signal ("async operations") |
| CI/CD configs | DevOps signal ("automated CI/CD pipeline") |
| Directory structure | Architecture signal ("MVC architecture") |
| Commit timeline | Duration ("developed over 6 months") |
| Commit count | Dedication signal |

### What We CANNOT Extract (User Must Provide)

- Business impact numbers (users, revenue, etc.)
- Team size and role
- Why the project was built
- Performance metrics (unless in code comments)

### Action Verbs by Category

| Category | Verbs |
|----------|-------|
| **Building** | Built, Developed, Implemented, Engineered, Architected, Created, Launched |
| **Improving** | Optimized, Improved, Enhanced, Streamlined, Refactored, Modernized |
| **Problem-Solving** | Resolved, Debugged, Troubleshot, Fixed, Addressed |
| **Leading** | Spearheaded, Orchestrated, Directed, Led, Coordinated |
| **Analyzing** | Analyzed, Evaluated, Investigated, Assessed, Identified |

---

## Prompt Engineering

### Pass 2 Prompt Template (File Analysis)

```
You are analyzing a developer's code contribution to understand what they built.

FILE: {file_path}
LANGUAGE: {language}
REPO: {repo_name}

The following is the code this developer added to this file
(extracted from their git commits):

---
{user_code_additions}
---

Analyze this code and respond in JSON:
{
  "purpose": "What does this code do? (1 sentence)",
  "technologies": ["List specific libraries/frameworks used"],
  "patterns": ["List design patterns or practices demonstrated"],
  "complexity": "beginner | intermediate | advanced",
  "highlights": ["1-2 most impressive things about this code"]
}

Be specific. Mention actual class names, function names, and libraries.
Do not guess about things not present in the code.
```

### Pass 3 Prompt Template (Project Synthesis)

```
You are a technical resume writer. Given the following analysis of a
developer's contributions to a project, write resume-quality content.

PROJECT: {repo_name}
LANGUAGES: {languages}
FRAMEWORKS: {frameworks}
TOTAL FILES CONTRIBUTED: {file_count}
DEVELOPMENT PERIOD: {first_commit} to {last_commit}

File-by-file analysis:
{json_summaries_from_pass_2}

Write:

1. PROJECT SUMMARY (2-3 sentences describing what was built)

2. RESUME BULLETS (3-5 bullet points)
   Format: "[Action verb] [what was built] using [specific technologies]"
   - Start each with a strong action verb (Built, Designed, Implemented, etc.)
   - Mention specific technologies by name
   - Include scale indicators where possible (number of endpoints, files, etc.)
   - Keep each bullet to 1-2 lines maximum

3. KEY TECHNOLOGIES (comma-separated list)

Rules:
- Be specific, not generic. Say "FastAPI" not "web framework"
- Only mention technologies actually present in the code analysis
- Do not invent metrics or numbers not supported by the analysis
- Sound professional and impressive without being dishonest
```

### Pass 4 Prompt Template (Portfolio Synthesis)

```
You are creating a developer portfolio profile from multiple project analyses.

PROJECTS ANALYZED:
{all_project_summaries_from_pass_3}

DEVELOPER EMAIL: {user_email}
TOTAL REPOSITORIES: {repo_count}

Write:

1. PROFESSIONAL SUMMARY (3-4 sentences)
   A paragraph suitable for the top of a resume that captures this
   developer's overall capabilities and experience.

2. SKILL PROGRESSION
   Show how the developer's skills evolved across projects.
   If they used the same technology in multiple projects, note growth.
   Format: "Technology: basic (Project A) → advanced (Project C)"

3. STRONGEST AREAS (top 3-5)
   What is this developer best at, based on evidence across all projects?

4. TECHNOLOGIES USED (categorized)
   Languages: ...
   Frameworks: ...
   Databases: ...
   Tools: ...

Rules:
- Synthesize across projects, don't just list them
- Show growth and progression where visible
- Be specific with technology names
- Only claim what the code evidence supports
```

---

## RAM Budget and Model Tiers

### Realistic RAM Breakdown (8GB M2 MacBook Air)

| Component | Usage |
|-----------|-------|
| macOS | 2.5-3.5 GB |
| Python + ArtifactMiner app | 500 MB - 1 GB |
| **Available for LLM** | **~3.5-4.5 GB** |

### What Fits

| Tier | Model | Q4 RAM | Fits on 8GB? | Notes |
|------|-------|--------|-------------|-------|
| Small | Qwen3-1.7B | ~1.5 GB | Yes, comfortable | Quality may be limited |
| Medium | Phi-4-mini | ~2.5 GB | Yes, comfortable | Best balance |
| Large | Qwen3-4B | ~3 GB | Yes, with care | Close to limit |
| XL | Qwen2.5-Coder-7B | ~5 GB | Tight, will swap | Slow but possible |

### Speed Expectations (M2 MacBook Air, Q4)

| Model | Tokens/sec | Pass 2 (per file) | Full Pipeline (3 repos, 15 files) |
|-------|-----------|-------------------|-----------------------------------|
| 1.7B | ~8-12 | ~15 seconds | ~5 minutes |
| 3.8B | ~4-6 | ~30 seconds | ~10 minutes |
| 4B | ~3-5 | ~40 seconds | ~13 minutes |
| 7B (Q4) | ~1-3 | ~90 seconds | ~30 minutes |
| Cloud API | N/A | ~3 seconds | ~1 minute |

All within the "10+ minutes is fine" constraint, except the 7B which may push 30 minutes for large portfolios.

---

## Relationship to Existing System

### What Stays

- Evan's `getRepoStats()`, `getUserRepoStats()`, `collect_user_additions()` - all stay as-is
- Evan's `generate_summaries_for_ranked()` - stays, runs alongside
- Shlok's `SkillExtractor` regex system - stays for fast skill detection
- Shlok's `DeepRepoAnalyzer` insights - stays
- Nathan's orchestration in `analyze.py` - stays, we add a new step

### What's New

A new module (e.g., `src/artifactminer/skills/resume_generator.py`) that:

1. Runs AFTER the existing analysis loop
2. Takes the already-collected data (repo stats, user additions, skills, insights)
3. Passes it through the multi-pass LLM pipeline
4. Produces resume artifacts
5. Stores them in the database

### Where It Plugs In

In `analyze.py`, after the existing analysis loop and before ranking:

```python
# ... existing analysis loop ...

# NEW: Generate resume artifacts via local LLM
if consent_level in ("full", "local_llm"):
    from ..skills.resume_generator import generate_resume_artifacts
    
    resume_artifacts = await generate_resume_artifacts(
        repos_analyzed=repos_analyzed,
        user_email=user_email,
        extraction_path=extraction_path,
        model_tier=user_selected_tier,  # "small", "medium", "large", "xl", "cloud"
        progress_callback=progress_callback,
    )

# ... existing ranking and summary code ...
```

---

## Open Questions

- [ ] Should we use tree-sitter for Pass 2 file analysis, or is raw code sufficient for most files?
- [ ] How should we handle files the user didn't fully write (e.g., they added 10 lines to a 500-line file)?
- [ ] Should Pass 4 (portfolio synthesis) run even if there's only 1 repo?
- [ ] What database table(s) store the resume artifacts?
- [ ] How does the TUI/CLI display the generated artifacts?
- [ ] Should we let users edit/refine the generated text before saving?
- [ ] How do we handle the case where Ollama is not installed?
- [ ] Should the cloud tier use the existing OpenAI integration or a new one?
- [ ] What's the minimum quality threshold? If output is bad (garbled JSON, etc.), should we retry or fall back?

---

## Appendix: Full Model Comparison

### Master Table

| Model | Params | Q4 RAM | Context | HumanEval | JSON Support | License | Code Focus |
|-------|--------|--------|---------|-----------|-------------|---------|------------|
| Phi-4-mini | 3.8B | ~2.5 GB | 128K | 62.8% | Native | MIT | Strong |
| Qwen3-4B | 4.0B | ~3 GB | 32K* | Claimed strong | Yes | Apache 2.0 | Strong |
| Qwen2.5-Coder-3B | 3.1B | ~2.5 GB | 32K | Not published | Yes | Qwen Research | Code-specialized |
| Qwen2.5-Coder-7B | 7B | ~5 GB | 32K | Strong | Yes | Qwen Research | Code-specialized |
| Gemma 3 4B | 4.0B | ~3 GB | 128K | 36.0% | Yes | Gemma | General |
| CodeGemma 2B | 2.0B | ~2 GB | ~8-32K | 31.1% | Yes | Gemma | Code-specialized |
| DS-R1-Distill 1.5B | 1.5B | ~1.5 GB | 32K | N/A | Via prompting | MIT | Reasoning |
| DeepSeek-Coder 1.3B | 1.3B | ~1.5 GB | 16K | SOTA for 1.3B | Via prompting | MIT-like | Code-specialized |
| Qwen3-1.7B | 1.7B | ~1.5 GB | 32K* | N/A | Yes | Apache 2.0 | General |
| LFM2.5-1.2B | 1.2B | ~2 GB | 32K | N/A | Yes | Custom** | General (5% code) |
| StarCoder2-3B | 3.0B | ~2 GB | 16K | 31.7% | No (base) | OpenRAIL | Code-specialized |
| Llama 3.2 3B | 3.2B | ~3.7 GB | 8K (quant) | N/A | Via grammar | Llama | General |
| Llama 3.2 1B | 1.2B | ~1.9 GB | 8K (quant) | N/A | Via grammar | Llama | General |

\* Extendable to 128K with YaRN
\** Free if revenue < $10M/year

### Model Notes

**Phi-4-mini:** Best code benchmarks in class. Native JSON. MIT license. Recommended default.

**Qwen3-4B:** Has unique "thinking mode" - shows reasoning in `<think>` tags. Apache 2.0. 36T training tokens.

**Qwen2.5-Coder-3B/7B:** Purpose-built for code (5.5T code tokens). Best for code understanding.

**Gemma 3 4B:** 128K native context. Good if analyzing very large files.

**DeepSeek-R1-Distill 1.5B:** Remarkably good reasoning for 1.5B params (83.9% MATH-500). MIT license. Best "small" option.

**LFM2.5-1.2B (Liquid AI):** Non-transformer architecture with constant memory. Fast inference. But only 5% code in training - weakness for our use case.

**Llama 3.2:** Context drops to 8K when quantized. Heaviest RAM for weakest code ability. Not recommended.

---

## Appendix: Approaches That Don't Work

### Why Agentic Fails (2-4B Models)

- No models under 7B have ever been benchmarked as coding agents
- Aider's smallest tested model is 32B (at 40% success rate)
- Agent overhead: 3K-10K tokens per step, 5-7 steps max in 32K context
- Latency: minutes per step on M2
- Tool calling requires 8B+ minimum in Ollama

### Why RAG Is Overkill Here

- We already have scoped data (user additions per file)
- Vector DB adds complexity without clear retrieval benefit
- The "retrieval" problem is solved by the discovery pass (Pass 1)
- 4.4x more tokens than post-processing for similar quality

### Why Pure Score Refinement Is Too Narrow

- The proficiency scores (0-1) are based on arbitrary constants
- Users want narratives, not numbers
- A score of 0.78 means nothing to a recruiter
- "Architected async API with dependency injection" is what matters

### Why Embedding Similarity Alone Is Insufficient

- Can detect skill presence (yes/no) but cannot generate text
- Cannot explain WHY a skill is demonstrated
- Cannot produce resume-quality narratives
- Moderate accuracy (70-80%) - too unreliable alone

---

## Appendix: Research Sources

### Map-Reduce for LLMs
- LangChain summarization tutorial
- LlamaIndex tree_summarize mode
- Research on hierarchical summarization with small models
- Information loss: ~20-30% per level of hierarchy

### Small Model Limitations
- Quality drops after 50-60% context filled for 2-4B models
- 7-8B models handle up to 80% context well
- Iterative refinement risky for small models (hallucination amplification)
- Single-pass preferred over multi-iteration for sub-4B

### Resume Writing Best Practices
- Laszlo Bock (former Google SVP) X-Y-Z formula
- Resume scan time: <6 seconds average
- One page maximum for early career
- Action verbs + specific technologies + quantifiable impact
- Existing tools (resume.github.io, gitconnected, JSON Resume) only do data display - none generate intelligent narratives

### Key Research Finding
> "A fine-tuned 0.3B model can exhibit substantial data refining capabilities comparable to human experts" (ProX paper, arXiv:2409.17115)

This validates that small models CAN produce quality output when the task is well-scoped and the input is structured - which is exactly what our multi-pass pipeline provides.
