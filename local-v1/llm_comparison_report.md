# LLM Resume Output Comparison Report

> **Models compared**: lfm2-2.6b-q8, lfm2-2.6b-exp-q8, lfm2.5-1.2b-instruct-bf16, qwen3-4b
> **Input**: `20260125_221350_mock_projects.zip` (8 repos, 178 total commits, 86 user-attributed)
> **Baseline**: Static analysis pipeline + ground-truth commit inspection

---

## 1. Ground Truth Baseline

### 1.1 Contribution Percentages

| Project | Actual (manual) | Pipeline-detected | All 4 LLMs |
|---------|:-:|:-:|:-:|
| algorithms-toolkit | 100% (18/18) | 100% | 100% |
| campus-navigation-api | 36% (9/25) | 36% | 36% |
| go-task-runner | 30% (7/23) | 30% | 30% |
| infra-terraform | **34% (8/23)** | 30% (7/23) | 30% |
| java-chat-service | **39% (9/23)** | 30% (7/23) | 30% |
| ml-lab-notebooks | **36% (8/22)** | 32% (7/22) | 32% |
| personal-portfolio-site | 100% (21/21) | 100% | 100% |
| sensor-fleet-backend | 43% (10/23) | 43% | 43% |

**Note**: infra-terraform, java-chat-service, and ml-lab-notebooks have commits under a secondary email (`106793433+shahshlok@users.noreply.github.com`) that the pipeline doesn't match on `shlok10@student.ubc.ca`. All 4 LLMs inherit this pipeline limitation — not an LLM error.

### 1.2 Commit Classification Ground Truth

Manual classification from conventional commit prefixes across all 90 user commits (with non-standard prefix mapping: `style:`→refactor, `a11y:`→feature, `content:/copy:/notes:`→docs):

| Category | Ground Truth (90) | lfm2-q8 (86) | lfm2-exp-q8 (86) | lfm2.5-1.2b (84) | qwen3-4b (86) |
|----------|:-:|:-:|:-:|:-:|:-:|
| **Feature** | 30 (33%) | 30 (35%) | 30 (35%) | 31 (37%) | **32 (37%)** |
| **Docs** | **24 (27%)** | **18 (21%)** | **18 (21%)** | **17 (20%)** | **17 (20%)** |
| **Test** | 15 (17%) | 15 (17%) | 14 (16%) | 15 (18%) | 15 (17%) |
| **Chore** | 15 (17%) | 14 (16%) | 14 (16%) | 16 (19%) | 15 (17%) |
| **Refactor** | 6 (7%) | 8 (9%) | 9 (10%) | 5 (6%) | 7 (8%) |
| **Bugfix** | **0 (0%)** | **1 (1%)** | **1 (1%)** | 0 (0%) | **0 (0%)** |

**Key findings**:
- All four **undercount docs by 7** — the non-standard prefixes (`content:`, `copy:`, `notes:`) are misclassified (likely into chore or feature)
- lfm2-q8 and lfm2-exp-q8 both **hallucinate 1 bugfix** that doesn't exist in the data
- lfm2.5-1.2b loses 6 commits entirely (84 vs 90 total), suggesting it dropped some during classification
- qwen3-4b **overcounts features by 2** (likely misclassifying docs or chore as feature)
- Feature and test counts are very accurate across all models

### 1.3 Style Metrics Baseline

The pipeline feeds only the **first project's** style metrics to the LLM (a known limitation at `generate.py:430`). In these runs, it used `personal-portfolio-site` (3 functions, 2 files):

| Metric | Fed to LLM (1 project) | True Aggregate (5 projects, 64 funcs) |
|--------|:-:|:-:|
| Avg function length | **7.7** | **4.1** |
| Naming convention | camelCase | mixed (mostly snake_case) |
| Comment density | 2.1 per 100 LOC | ~0.3 per 100 LOC |
| Type annotation ratio | 0.00 | ~0.08 |
| Docstring coverage | 0.00 | 0.00 |

The data given to the LLMs is technically correct but **misleading** — it represents a single project (3 JavaScript functions), not the portfolio. This is a **pipeline bug**, not an LLM error.

### 1.4 Complexity Baseline

Top 5 complex files (ground truth):

| File | Cyclomatic Complexity | Max Nesting | LOC |
|------|:-:|:-:|:-:|
| algorithms-toolkit/search.py | 13 | 4 | 40 |
| algorithms-toolkit/sorting.py | 6 | 3 | 30 |
| algorithms-toolkit/cli.py | 6 | 4 | 31 |
| algorithms-toolkit/test_search.py | 5 | 1 | 16 |
| campus-navigation-api/dist/index.js | 5 | 1 | 29 |

Average CC across top 5: **7.0**, max nesting depth: **4**.

### 1.5 Template Baseline (No LLM)

The static pipeline without LLM produces generic bullets like:
```
- Contributed 43% of commits to sensor-fleet-backend, a FastAPI/Python project
- Demonstrated proficiency in Technical Writing, Python, FastAPI, Data Validation
- Built features using FastAPI, Data Validation, Testing
```
No skill evolution, developer profile, complexity narrative, or work breakdown sections.

---

## 2. Factual Accuracy

### 2.1 Technology & Skills Claims

| Claim | lfm2-q8 | lfm2-exp-q8 | lfm2.5-1.2b | qwen3-4b | Verdict |
|-------|:-:|:-:|:-:|:-:|---------|
| Python, Go, JS, TS | Y | Y | Y | Y | **Correct** — all present |
| FastAPI, Express | Y | Y | Y | Y | **Correct** — present in repos |
| Pydantic, Uvicorn | Y | - | - | Y | **Valid inference** — in requirements.txt |
| pytest | Y | - | - | Y | **Valid** — used in tests |
| Terraform | Y (infra) | - | Y (infra) | - | **Valid** — infra-terraform |
| CLI Parsing | Y | - | - | - | **Valid** — argparse in algorithms-toolkit |
| React | - | - | **Y** | **Y** | **HALLUCINATED** — no React in any project |
| NumPy, Pandas, Scikit-learn | - | - | **Y** | Y | **Correct** — in ml-lab-notebooks/requirements.txt |
| Docker | - | - | **Y** | - | **HALLUCINATED** — no Dockerfile anywhere |
| AWS | - | - | **Y** | - | **HALLUCINATED** — no AWS references |
| AWS CloudFormation | - | - | **Y** | - | **HALLUCINATED** — no CloudFormation |
| HTML, CSS | - | - | - | Y | **Valid** — portfolio-site has index.html, styles.css |

**Hallucination count**: lfm2-q8: **0**, lfm2-exp-q8: **0**, lfm2.5-1.2b: **3**, qwen3-4b: **1** (React)

### 2.2 Fabricated Metrics

| Claim | Model | Verdict |
|-------|-------|---------|
| "reducing false positives by 40%" | lfm2-q8 | **FABRICATED** — no metric in commit data |
| "sub-second response times" | lfm2-q8 | **FABRICATED** — no perf data exists |
| "improving data accuracy by 15% under high load" | lfm2-q8 | **FABRICATED** — no benchmark data |
| "across 23 commits" (uptime feature) | lfm2.5-1.2b | **MISLEADING** — 23 is total repo commits, user has 10 |
| "covering 15 critical scenarios" (test suite) | lfm2.5-1.2b | **FABRICATED** — user has 4 test commits |
| "100% validation coverage" (csv export) | lfm2.5-1.2b | **UNVERIFIABLE** — no coverage data |
| "across 7 commits" (cost center) | lfm2.5-1.2b | **MISLEADING** — user has 1 cost center commit |
| "with 4 commits" (stage env) | lfm2.5-1.2b | **FABRICATED** — user has 1 stage env commit |
| "5+ years of experience" | qwen3-4b | **FABRICATED** — repos span 2020-2021 (~1 year) |
| "O(1) space complexity" (rotate) | qwen3-4b | **UNVERIFIABLE** — algorithmic claim not in commits |
| "optimized path reconstruction" (dijkstra) | qwen3-4b | **UNVERIFIABLE** — implementation detail not in commits |
| "pagination support" (fetch latest) | qwen3-4b | **FABRICATED** — no pagination in commit data |
| "unique identifiers and geographic metadata" | qwen3-4b | **FABRICATED** — specific fields not in commits |
| "real-time sensor alerting" | qwen3-4b | **EMBELLISHMENT** — no "real-time" mentioned |

**Fabricated metric count**: lfm2-q8: **3**, lfm2-exp-q8: **0**, lfm2.5-1.2b: **5+**, qwen3-4b: **6+**

### 2.3 Structural Accuracy Issues

| Issue | Model | Details |
|-------|-------|---------|
| `/stale_sensor` endpoint | lfm2-q8 | `stale_sensors` is a helper function, not an endpoint. Commit is "test: stale sensor path" (a test) |
| "resource management system with chunking" | lfm2-exp-q8 | No evidence in any commit or code |
| "chore: seed modules and dev env" | lfm2-exp-q8 | Raw commit prefix leaked into bullet text |
| "18 commits covering 6 features" | lfm2-exp-q8 | Meta-description, not a resume bullet |
| "SEO best practices in the codebase" | lfm2.5-1.2b | Commit was "docs: jot seo todo" — just a note |
| "support high traffic scenarios" | lfm2.5-1.2b | No evidence in java-chat-service |
| Skills section truncated: "Pra" | lfm2.5-1.2b | Output was cut off mid-word |
| "Summary:" / "SKILLS:" prefix | lfm2.5-1.2b | Formatting leak — LLM echoed prompt markers |

---

## 3. Prose Quality

### 3.1 Professional Summary

| Model | Text | Assessment |
|-------|------|------------|
| **lfm2-q8** | "A versatile full-stack developer with expertise in Python, Go, JavaScript, and TypeScript, specializing in building scalable backends, data pipelines, and robust APIs..." | **Strong**: specific, professional, well-structured. Mentions concrete domains. |
| **lfm2-exp-q8** | "Experienced full-stack developer with expertise in building scalable APIs, data pipelines, and robust systems across diverse technologies..." | **Good**: concise and professional, but more generic. |
| **lfm2.5-1.2b** | "Summary: Experienced professional with a strong portfolio spanning diverse technical projects..." | **Weak**: starts with "Summary:" prefix (formatting leak). Vague language ("strong portfolio", "diverse technical projects"). |

**Winner**: lfm2-q8

### 3.2 Project Bullets

**Bullet count per project**:

| Project | lfm2-q8 | lfm2-exp-q8 | lfm2.5-1.2b | User commits |
|---------|:-:|:-:|:-:|:-:|
| go-task-runner | 5 | 4 | 5 | 7 |
| personal-portfolio-site | **7** | 3 | 5 | 21 |
| sensor-fleet-backend | **6** | 5 | **7** | 10 |
| infra-terraform | 4 | 4 | **6** | 7-8 |
| algorithms-toolkit | 5 | 5 | **7** | 18 |
| java-chat-service | 5 | 4 | **6** | 7-9 |
| campus-navigation-api | 4 | 3 | **6** | 9 |
| ml-lab-notebooks | 3 | 4 | 5 | 7-8 |
| **Total bullets** | **39** | **32** | **47** | — |

**Bullet quality assessment**:

**lfm2-q8** — Best specificity:
- References specific code artifacts: `json.Marshal`, `saveResults`, `configValidation`
- Inline commit message citations provide traceability
- Action verbs are strong: "Implemented", "Mapped", "Designed"
- **Weakness**: fabricates quantitative metrics (40%, 15%), some redundancy in personal-portfolio-site (skills section mentioned twice)

**lfm2-exp-q8** — Most concise:
- Each bullet is 1 line, very clean
- Minimal hallucination — sticks close to commit messages
- Good action verb variety: "Architected", "Designed", "Developed"
- **Weakness**: TOO terse — bullets lack impact and specificity. "Architected alerts endpoint with validation and DI" doesn't say what it actually does
- Format leak: "Independently built chore: seed modules" (raw prefix)
- Meta-bullet: "Independently built 18 commits covering 6 features" — not useful as a resume bullet

**lfm2.5-1.2b** — Most verbose:
- Most "resume-like" prose with strong action verbs
- Good narrative flow within each project section
- **Weakness**: the most hallucinations of the three — fabricated metrics, wrong commit counts, invented technologies. Quantity over accuracy.

### 3.3 Narrative Sections

**Skill Evolution**:

| Model | Text | Assessment |
|-------|------|------------|
| lfm2-q8 | "Over the past three years, my technical expertise has evolved from foundational languages like Java and Go to a more comprehensive full-stack and data-focused skill set..." | **Good**: specific trajectory, mentions concrete transitions. Uses first person (inconsistent with rest of resume). |
| lfm2-exp-q8 | "This developer evolved from foundational Java and Go skills to mastering Python, TypeScript, and robust testing practices..." | **OK**: concise but generic. Single sentence. Third person (consistent). |
| lfm2.5-1.2b | "My technical journey showcases a steady progression from foundational languages like Java and Go to modern frameworks such as Python and TypeScript..." | **Best**: most detailed, mentions specific milestones (portfolio → backend → ML notebooks). Uses first person. |

**Developer Profile**:

| Model | Assessment |
|-------|------------|
| lfm2-q8 | **Best**: cites specific metrics (7.7 lines, camelCase, 2.1 comments/100 LOC). Accurately notes limited type annotations and no docstrings. |
| lfm2-exp-q8 | **OK**: mentions 7.7 lines but omits other metrics. |
| lfm2.5-1.2b | **Worst**: completely ignores the style metrics data. Generic platitude: "A concise and maintainable developer." |

**Complexity Highlights**:

| Model | Assessment |
|-------|------------|
| lfm2-q8 | **Best**: cites "3.9 CC and max depth 4". The 3.9 doesn't match my calculation (7.0 avg) but does cite specific numbers. |
| lfm2-exp-q8 | **Weak**: vague, no numbers. Also ends with a comma instead of a period (grammatical error). |
| lfm2.5-1.2b | **Weak**: "efficiently handling 20 complex files" — vague, number doesn't match (19 files analyzed). |

---

## 4. Formatting & Structure

| Dimension | lfm2-q8 | lfm2-exp-q8 | lfm2.5-1.2b | qwen3-4b |
|-----------|:-:|:-:|:-:|:-:|
| All sections present | Yes | Yes | Yes | Yes |
| Clean markdown | Yes | Yes | **No** — truncated "Pra" | Yes |
| Skills categorization | 4 categories | 3 categories | 4 categories (hallucinated) | 3 categories |
| Consistent voice | Mostly (first/third mix) | Yes (third person) | **No** (first/third mix) | Yes (third person) |
| Grammar/punctuation | Clean | Trailing comma | Clean | Clean |
| Output length | 128 lines | 121 lines | 135 lines | 128 lines |
| Generation time | 408.0s | 303.2s | **216.2s** | **1052.8s** |

---

## 5. Scoring Summary

### Per-dimension scores (1-5, where 5 = best)

| Dimension | lfm2-q8 | lfm2-exp-q8 | lfm2.5-1.2b | qwen3-4b |
|-----------|:-:|:-:|:-:|:-:|
| Factual accuracy (technologies) | **5** | **5** | **2** | **4** |
| Factual accuracy (metrics) | **2** | **5** | **1** | **2** |
| Commit classification | 4 | 4 | 3 | 4 |
| Bullet specificity | **5** | 3 | 4 | **5** |
| Bullet accuracy | 3 | **4** | 2 | 3 |
| Prose quality (summary) | **5** | 4 | 2 | 4 |
| Prose quality (narratives) | **4** | 3 | 3 | **5** |
| Developer profile fidelity | **5** | 3 | 1 | 4 |
| Formatting/structure | **5** | 4 | 2 | **5** |
| Completeness | **5** | 3 | 4 | **5** |
| **TOTAL** | **43/50** | **38/50** | **24/50** | **41/50** |

### Overall Rankings

| Rank | Model | Strengths | Weaknesses |
|:----:|-------|-----------|------------|
| **1** | **lfm2-2.6b-q8** | Most specific bullets, best prose quality, best structure, accurate technology claims | Fabricates quantitative metrics (40%, 15%), some bullet redundancy |
| **2** | **qwen3-4b** | Excellent narrative sections, consistent formatting, very professional tone, no fabricated percentages | Slowest generation (1052s), hallucinates React, fabricates algorithmic details and timeline ("5+ years") |
| **3** | **lfm2-2.6b-exp-q8** | Most honest/conservative, fewest hallucinations, fastest accuracy-to-speed ratio | Too terse for resume use, some format leaks, vague narratives |
| **4** | **lfm2.5-1.2b** | Fastest generation (216s), good narrative flow | Most hallucinations (React, Docker, AWS, fabricated metrics), truncated output, formatting leaks |

---

## 6. Recommendations

### For Resume Quality
**lfm2-2.6b-q8 remains the winner** for production resume generation — best balance of specificity, structure, and professionalism. **qwen3-4b is a close second** with superior narrative sections but slower generation.

### For Speed + Quality
**qwen3-4b offers the best output quality among larger models** (41/50 score) but is **5x slower** than lfm2-q8 (1052s vs 408s). If time isn't critical, qwen3-4b produces more polished narratives.

### For Truthfulness
**lfm2-2.6b-exp-q8 is the safest choice** — it rarely hallucinates but needs prompt tuning to produce longer, more impactful bullets.

### For Speed
**lfm2.5-1.2b is fastest (216s)** but too unreliable for production use due to hallucinations and truncation.

### Pipeline Improvements Needed
1. **Email matching**: Support multiple emails per user (noreply GitHub email misses ~4 commits)
2. **Style metrics aggregation**: Aggregate across ALL projects, not just the first (`generate.py:430`)
3. **Non-standard commit prefixes**: Teach the classifier about `style:`, `a11y:`, `content:`, `copy:`, `notes:`
4. **Prompt guardrails**:
   - "NEVER fabricate quantitative metrics or timelines"
   - "NEVER invent pagination, geographic metadata, or algorithmic complexity claims not in commit messages"
   - "Use technical terms (Pydantic, pytest) only when verifiable from project files"

### Models to Avoid
**lfm2.5-1.2b** — Hallucinates entire technology stacks (React, Docker, AWS), truncates output, formatting leaks. Speed (216s) doesn't justify accuracy cost.

---

*Report generated from ground-truth analysis of 8 mock repositories, 90 user commits, cross-referenced against 3 LLM outputs.*
