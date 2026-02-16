# Context Engineering Overhaul — Architecture Plan

## Constraints & Targets

- **Hardware**: MacBook Air M2, 8GB RAM — one model loaded at a time
- **Models**: Any ≤4B params. Primary candidate: LFM2.5-1.2B-Instruct (731MB Q4_K_M)
- **Effective context**: 2K–4K tokens per LLM call (regardless of advertised window)
- **Quality over speed**: Generation time doesn't matter yet
- **Output**: Raw material is fine — multiple LLM stages will refine it
- **Average input**: ~6 repos per user upload

## Current Architecture

```
ZIP upload
  └─ extract_zip() + discover_git_repos()
       └─ For each repo: _extract_project()
            ├── getRepoStats()           (existing: languages, commits, frameworks)
            ├── getUserRepoStats()       (existing: contribution %, commit dates)
            ├── collect_user_additions()  (existing: raw diff text)
            ├── DeepRepoAnalyzer         (existing: skills, evidence, insights)
            ├── build_project_facts()    (existing: intermediate facts object)
            ├── extract_readme()         (v3: first 600 chars)
            ├── extract_and_classify_commits()  (v3: regex + LLM fallback)
            ├── extract_structure()      (v3: dir overview + user-touched files)
            ├── extract_constructs()     (v3: routes, classes, tests, functions)
            └── infer_project_type()     (v3: web api / cli / library / etc.)
       └─ _build_portfolio()  (aggregate across repos)
       └─ For each bundle: run_project_query()     (1 LLM call per project)
       └─ run_portfolio_queries()                   (3 LLM calls total)
       └─ assemble_markdown() + assemble_json()
```

### Current Data Flow Into LLM

`ProjectDataBundle.to_prompt_context()` (models.py:116-173) builds the text that each per-project LLM call receives. Current truncation limits:

| Signal              | Limit        | Problem                           |
|---------------------|--------------|-----------------------------------|
| README              | 600 chars    | Arbitrary, may cut mid-sentence   |
| Languages           | Top 4        | Drops minor but relevant languages|
| Commits per category| 10 each      | No ranking — just first 10        |
| Routes/Classes/Functions | 8 each  | No importance ranking             |
| Modules             | 6            | No ranking by user activity       |

### Current Prompt Issues (prompts.py)

- Zero-shot (no examples)
- 7 negative instructions ("Never invent", "Do NOT", etc.)
- No per-model sampling parameters
- System prompt is one dense paragraph

### Current LLM Call Pattern

- N project calls (1 per repo, ~768 max_tokens each)
- 3 portfolio calls (summary, skills, profile — 256/320/320 max_tokens)
- All use same temperature (0.15) regardless of model
- No distillation step between extraction and LLM

---

## Strategy A: Extract More + Distill Aggressively

**Goal**: Get more signal out of the git repos, then compress it intelligently for the LLM.

### A1. New Extractors

Add to `extractors/` — each is a new file or addition to existing file.

#### `extractors/git_stats.py` (NEW — ~80 lines)

Extract quantitative impact signals per user per repo:

```
extract_git_stats(repo_path, user_email) -> GitStats
```

Fields:
- `lines_added: int` — total lines added by user across all commits
- `lines_deleted: int` — total lines deleted by user
- `net_lines: int` — lines_added - lines_deleted
- `files_touched: int` — unique files modified by user
- `file_hotspots: list[tuple[str, int]]` — top 10 files by edit frequency
- `active_days: int` — number of distinct days with commits
- `active_span_days: int` — first commit to last commit span
- `avg_commit_size: float` — average lines changed per commit

Data source: `git log --numstat --author=<email>` via GitPython.

#### `extractors/test_ratio.py` (NEW — ~40 lines)

Compute test-to-source file ratio:

```
extract_test_ratio(repo_path, user_email) -> TestRatio
```

Fields:
- `test_files: int` — count of test files touched by user
- `source_files: int` — count of non-test source files touched by user
- `test_ratio: float` — test_files / source_files (0 if no source)
- `has_ci: bool` — presence of .github/workflows/, .gitlab-ci.yml, Jenkinsfile

Data source: File listing from structure extractor + glob patterns.

#### `extractors/commit_quality.py` (NEW — ~50 lines)

Score overall commit quality:

```
extract_commit_quality(commit_groups) -> CommitQuality
```

Fields:
- `conventional_pct: float` — % of commits matching conventional format
- `avg_message_length: float` — average chars per commit subject
- `type_diversity: int` — number of distinct commit categories used
- `longest_streak: int` — longest consecutive-day commit streak

Data source: Already-classified commit groups from `extract_and_classify_commits()`.

#### `extractors/cross_module.py` (NEW — ~40 lines)

Measure breadth of contribution across the codebase:

```
extract_cross_module_breadth(module_groups) -> ModuleBreadth
```

Fields:
- `modules_touched: int` — count of top-level directories with user changes
- `total_modules: int` — count of all top-level directories
- `breadth_pct: float` — modules_touched / total_modules
- `deepest_path: str` — deepest nested file path touched by user

Data source: Already-extracted `module_groups` from `extract_structure()`.

### A2. New Data Models

Add to `models.py`:

```python
@dataclass
class GitStats:
    lines_added: int = 0
    lines_deleted: int = 0
    net_lines: int = 0
    files_touched: int = 0
    file_hotspots: list[tuple[str, int]] = field(default_factory=list)
    active_days: int = 0
    active_span_days: int = 0
    avg_commit_size: float = 0.0

@dataclass
class TestRatio:
    test_files: int = 0
    source_files: int = 0
    test_ratio: float = 0.0
    has_ci: bool = False

@dataclass
class CommitQuality:
    conventional_pct: float = 0.0
    avg_message_length: float = 0.0
    type_diversity: int = 0
    longest_streak: int = 0

@dataclass
class ModuleBreadth:
    modules_touched: int = 0
    total_modules: int = 0
    breadth_pct: float = 0.0
    deepest_path: str = ""
```

Add fields to `ProjectDataBundle`:
```python
git_stats: GitStats = field(default_factory=GitStats)
test_ratio: TestRatio = field(default_factory=TestRatio)
commit_quality: CommitQuality = field(default_factory=CommitQuality)
module_breadth: ModuleBreadth = field(default_factory=ModuleBreadth)
```

### A3. Distillation Stage — `distill.py` (NEW — ~200 lines)

New module: `src/artifactminer/resume/distill.py`

This sits between EXTRACT and QUERY. It takes a `ProjectDataBundle` and produces a `DistilledContext` — a token-budgeted, ranked, deduplicated text block ready for the LLM.

```
distill_project_context(bundle: ProjectDataBundle, token_budget: int = 2500) -> DistilledContext
distill_portfolio_context(portfolio: PortfolioDataBundle, token_budget: int = 2000) -> DistilledContext
```

#### Distillation Logic

1. **Signal ranking** — Each signal type gets a resume-relevance weight:
   - Quantitative impact (lines, commits, contribution%) → HIGH
   - Concrete constructs (routes, classes, functions) → HIGH
   - Commit messages (features > bugfixes > refactors > rest) → MEDIUM
   - README excerpt → MEDIUM (but position-aware: use as intro)
   - Directory structure → LOW (only if breadth is notable)
   - Skills/frameworks → MEDIUM (already known, reinforcement value)

2. **Commit deduplication** — Group near-duplicate commit messages:
   - Normalize: lowercase, strip prefix, strip ticket numbers
   - Cluster by Jaccard similarity (word-level, threshold 0.6)
   - Keep best representative per cluster (longest, most specific)

3. **Token budgeting** — Allocate budget across sections:
   - Identity block (name, type, stack, contribution): ~200 tokens (fixed)
   - README excerpt: ~300 tokens (smart truncation at sentence boundary)
   - Quantitative signals: ~200 tokens (formatted as key: value pairs)
   - Commit highlights: ~800 tokens (ranked, deduplicated)
   - Code constructs: ~400 tokens (ranked by diversity, not just first-N)
   - Module breadth: ~100 tokens (only if notable)
   - Buffer: ~400 tokens for prompt overhead + few-shot example

4. **Output format** — Bullet-point sections with clear labels:
   ```
   PROJECT: <name>
   Type: <project_type> | Stack: <languages> | Contribution: <pct>%

   IMPACT:
   - Added <N> lines across <M> files over <D> active days
   - <contribution>% of codebase, touched <breadth>% of modules
   - Test coverage: <ratio> (test files to source files)

   KEY WORK (from commits):
   - <top ranked feature commit>
   - <top ranked feature commit>
   - <top ranked bugfix commit>

   CODE CONSTRUCTS:
   - Routes: GET /api/users, POST /api/auth, ...
   - Classes: UserService, AuthMiddleware, ...
   - Key functions: authenticate, validate_token, ...

   README SUMMARY:
   <sentence-boundary-truncated excerpt>
   ```

### A4. Pipeline Integration

Update `pipeline.py`:
- After `_extract_project()`, call new extractors
- Before `run_project_query()`, call `distill_project_context()`
- Pass `DistilledContext.text` to the LLM instead of `bundle.to_prompt_context()`

New pipeline flow:
```
EXTRACT → NEW EXTRACTORS → DISTILL → QUERY → ASSEMBLE
```

### A5. Tests

- `tests/resume/test_git_stats.py` — test each new extractor on a temp git repo
- `tests/resume/test_distill.py` — test distillation with mock bundles
- Test token budget enforcement
- Test commit deduplication
- Test signal ranking

---

## Strategy C: Small-Model-Optimized Prompts

**Goal**: Rewrite all prompts and parameters for how small (≤4B) models actually work.

### C1. Add Few-Shot Examples (prompts.py)

Add 1 concrete example to `build_project_prompt()`:

```
EXAMPLE INPUT:
PROJECT: TaskTracker
Type: Web Application | Stack: Python (72%), JavaScript (28%) | Contribution: 85%
IMPACT:
- Added 2,400 lines across 34 files over 45 active days
...

EXAMPLE OUTPUT:
DESCRIPTION: A full-stack task management application with real-time updates...
BULLETS:
- Built REST API with 12 endpoints for task CRUD operations using FastAPI
- Implemented WebSocket-based notifications reducing polling overhead
- Added role-based access control with JWT authentication
NARRATIVE: Contributed 85% of the codebase over 45 days...
```

Key constraint: Example must be ~200-300 tokens. Use a realistic but generic project.

### C2. Rewrite Negative → Positive Instructions (prompts.py)

Current (7 negatives):
```
- Never invent features, endpoints, classes, tools, or outcomes.
- Do not imply sole ownership.
- Do NOT use placeholder phrases like "various technologies".
```

Rewrite as positive:
```
- Reference only features, endpoints, and tools that appear in the data.
- Describe your specific role within the team.
- Name the exact technologies used.
```

### C3. Front-Load Output Format (prompts.py)

Move the output format spec to the TOP of the prompt (before data):
```
Your task: write a resume section in this exact format:
DESCRIPTION: [1 sentence]
BULLETS:
- [bullet 1]
- [bullet 2]
- [bullet 3]
NARRATIVE: [1 sentence]

Here is the project data:
<data>
```

Small models attend more to the beginning and end of context.

### C4. Per-Model Sampling Parameters (llm_client.py + runner.py)

Add to `MODEL_REGISTRY` or a parallel config:

```python
MODEL_SAMPLING: dict[str, dict] = {
    "lfm2.5-1.2b-*": {"temperature": 0.1, "top_p": 0.1, "repetition_penalty": 1.05},
    "qwen2.5-coder-*": {"temperature": 0.15, "top_p": 0.9},
    "qwen3-*": {"temperature": 0.2, "top_p": 0.9},
    "default": {"temperature": 0.2, "top_p": 0.9},
}
```

Update `query_llm_text()` to accept and pass `top_p` and `repetition_penalty` via `extra_body`.

### C5. Position-Aware Ordering (distill.py, models.py)

When building context for the LLM:
- **First**: Identity + quantitative impact (most important, beginning attention)
- **Middle**: Commit messages, code constructs (bulk data)
- **Last**: README excerpt + skills (end attention boost)

This is already handled by the distillation format in Strategy A, so C5 is a refinement.

### C6. Fix MODEL_REGISTRY (llm_client.py)

Current broken entries:
```python
"lfm2-2.6b-q8": ("meta-llama/Llama-2-2.6b-GGUF", ...)  # WRONG repo
"lfm2.5-1.2b-bf16": ("meta-llama/Llama-2.5-1.2B-Instruct-GGUF", ...)  # WRONG repo
```

Fix to:
```python
"lfm2-2.6b-q8": ("LiquidAI/LFM2-2.6B-GGUF", "LFM2-2.6B-Q8_0.gguf", 20480),
"lfm2.5-1.2b-q4": ("LiquidAI/LFM2.5-1.2B-Instruct-GGUF", "LFM2.5-1.2B-Instruct-Q4_K_M.gguf", 32768),
"lfm2.5-1.2b-bf16": ("LiquidAI/LFM2.5-1.2B-Instruct-GGUF", "LFM2.5-1.2B-Instruct-BF16.gguf", 32768),
```

### C7. Tests

- `tests/resume/test_prompts_v2.py` — verify few-shot example is included, no negative instructions, format is front-loaded
- Parameterized tests for each prompt builder function
- Verify token count of prompts stays within budget

---

## Strategy B: Multi-Stage Pipeline with Specialized Models

**Goal**: Replace single-pass LLM with a 3-stage pipeline, each stage using a model matched to the task.

### B1. Pipeline Stages

```
Stage 1: EXTRACT + DISTILL  (deterministic, no LLM)
    ↓
Stage 2: RAW GENERATION     (LFM2.5-1.2B — structured data extraction)
    ↓
Stage 3: DRAFT              (Qwen3-1.7B — first draft, shown to user)
    ↓
    [USER FEEDBACK]          (user reviews draft, provides corrections/preferences)
    ↓
Stage 4: POLISH             (Qwen3-4B — prose refinement with user feedback)
    ↓
    FINAL RESUME
```

### B2. Stage 2 — Raw Generation (LFM2.5-1.2B)

Input: `DistilledContext` from Stage 1
Output: Structured facts per project (not prose — just extracted claims)

This stage uses the extraction-optimized model to identify:
- What the project does (1 sentence)
- Key technical achievements (3-5 bullet facts)
- Developer's specific contribution

The output is **raw material**, not polished text. Format:

```
PROJECT_SUMMARY: <what it does>
FACTS:
- <fact 1>
- <fact 2>
- <fact 3>
ROLE: <developer's contribution>
```

### B3. Stage 3 — Draft (Qwen3-1.7B)

Input: Raw facts from Stage 2 + portfolio context
Output: First-draft resume (markdown)

This stage:
- Converts raw facts into natural resume prose
- Generates professional summary
- Generates skills section
- Produces a complete first-draft resume

This draft is **shown to the user** for feedback.

### B4. User Feedback Interface

Between Stage 3 and Stage 4, the user can:
- Edit/correct any section
- Add missing information
- Remove inaccurate claims
- Specify tone preferences

This feedback is captured as a structured diff or instruction set.

### B5. Stage 4 — Polish (Qwen3-4B)

Input: First draft + user feedback
Output: Final polished resume

This stage:
- Applies user corrections
- Improves prose quality and flow
- Ensures consistent tone
- Produces the final document

### B6. Model Orchestration

Update `pipeline.py` with a new `generate_resume_v3_multistage()`:

```python
def generate_resume_v3_multistage(
    zip_path: str,
    user_email: str,
    *,
    stage1_model: str = "lfm2.5-1.2b-q4",
    stage2_model: str = "qwen3-1.7b-q8",
    stage3_model: str = "qwen3-4b-q4",
    user_feedback: Optional[dict] = None,
    progress_callback: Optional[Callable[[str], None]] = None,
) -> ResumeOutput:
```

Model switching uses existing `_restart_server()` — ~4-6s per switch on M2.

### B7. New Models for Pipeline

Add to `MODEL_REGISTRY`:
```python
"lfm2.5-1.2b-q4": ("LiquidAI/LFM2.5-1.2B-Instruct-GGUF", "LFM2.5-1.2B-Instruct-Q4_K_M.gguf", 32768),
"qwen3-1.7b-q8": ("unsloth/Qwen3-1.7B-Instruct-GGUF", "Qwen3-1.7B-UD-Q8_K_XL.gguf", 32768),
"qwen3-4b-q4": ("unsloth/Qwen3-4B-Instruct-2507-GGUF", "Qwen3-4B-Instruct-2507-Q4_K_M.gguf", 20480),
```

### B8. Tests

- `tests/resume/test_pipeline_multistage.py` — integration tests with mocked LLM
- Test model switching between stages
- Test user feedback application
- Test each stage independently

---

## Implementation Order

### Phase 1: Strategy A (Extract + Distill)
1. Add new data models to `models.py`
2. Implement `extractors/git_stats.py`
3. Implement `extractors/test_ratio.py`
4. Implement `extractors/commit_quality.py`
5. Implement `extractors/cross_module.py`
6. Implement `distill.py`
7. Wire into `pipeline.py`
8. Write tests for all new code
9. Verify existing tests still pass

### Phase 2: Strategy C (Prompt Optimization)
1. Fix `MODEL_REGISTRY` in `llm_client.py`
2. Add per-model sampling to `llm_client.py` + `runner.py`
3. Rewrite `prompts.py` — few-shot, positive instructions, front-loaded format
4. Update `runner.py` to use per-model params
5. Write tests for prompt changes
6. Verify existing tests still pass

### Phase 3: Strategy B (Multi-Stage)
1. Add `generate_resume_v3_multistage()` to `pipeline.py`
2. Add stage-specific prompt templates to `prompts.py`
3. Add user feedback model to `models.py`
4. Update `cli.py` with multi-stage command
5. Write integration tests
6. Verify existing tests still pass

---

## Files Modified/Created

### Modified
- `src/artifactminer/resume/models.py` — new dataclasses + fields on ProjectDataBundle
- `src/artifactminer/resume/pipeline.py` — new extractors, distill step, multi-stage entry
- `src/artifactminer/resume/queries/prompts.py` — rewritten prompts
- `src/artifactminer/resume/queries/runner.py` — per-model sampling
- `src/artifactminer/resume/llm_client.py` — MODEL_REGISTRY fixes, sampling params
- `src/artifactminer/resume/assembler.py` — support multi-stage output
- `src/artifactminer/resume/cli.py` — new CLI commands
- `src/artifactminer/resume/extractors/__init__.py` — export new extractors

### Created
- `src/artifactminer/resume/extractors/git_stats.py`
- `src/artifactminer/resume/extractors/test_ratio.py`
- `src/artifactminer/resume/extractors/commit_quality.py`
- `src/artifactminer/resume/extractors/cross_module.py`
- `src/artifactminer/resume/distill.py`
- `tests/resume/test_git_stats.py`
- `tests/resume/test_distill.py`
- `tests/resume/test_prompts_v2.py`
- `tests/resume/test_pipeline_multistage.py`
