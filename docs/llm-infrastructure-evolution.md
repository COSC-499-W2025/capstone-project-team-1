# LLM Infrastructure Evolution: Ollama → llama-cpp-python → llama-server

**Branch:** `feature/llm-cpp-analysis`
**Last updated:** February 2026

This document traces the three generations of LLM infrastructure in Artifact Miner's resume pipeline, why each migration happened, and the current architecture.

---

## Table of Contents

1. [Timeline Overview](#1-timeline-overview)
2. [Generation 1: Ollama Daemon](#2-generation-1-ollama-daemon)
3. [Generation 2: llama-cpp-python (Embedded)](#3-generation-2-llama-cpp-python-embedded)
4. [Generation 3: llama-server (Current)](#4-generation-3-llama-server-current)
5. [Architecture Deep Dive](#5-architecture-deep-dive)
6. [Model Management](#6-model-management)
7. [Inference Call Types](#7-inference-call-types)
8. [Prompt Hardening Journey](#8-prompt-hardening-journey)
9. [Files Reference](#9-files-reference)
10. [Appendix: Evaluated Models](#appendix-evaluated-models)

---

## 1. Timeline Overview

```
 Commit History (feature/llm-cpp-analysis)
 ──────────────────────────────────────────

 ba028a1  Refactor: ollama helper import
 e54298e  chore: update deps for resume
 dc24e79  refactor: convert ollama test                    ┐
 cb9ca6b  feat: add resume generation module               │  Gen 1: Ollama
 ddb14f0  refactor: Static-First, LLM-Light architecture   │  (external daemon)
 74ca722  Require Ollama for LLM enhancement               ┘
 ─────────────────────────── migration #1 ───────────────────────────
 4c67752  llama.cpp python                                 ┐
 57a451c  feat: disable thinking mode, strip reasoning     │  Gen 2: llama-cpp-python
 6e1b17e  feat: replace Ollama + 4 new analysis features   │  (embedded in Python)
 2b78d76  feat: resume generation features + project facts ┘
 ─────────────────────────── migration #2 ───────────────────────────
 6de6159  feat: llama-server + reasoning-format deepseek     Gen 3: llama-server
                                                             (C++ subprocess)
```

### Side-by-side comparison

```
┌──────────────────────┬──────────────────┬────────────────────┬────────────────────┐
│                      │ Gen 1: Ollama    │ Gen 2: llama-cpp-  │ Gen 3: llama-      │
│                      │                  │ python             │ server             │
├──────────────────────┼──────────────────┼────────────────────┼────────────────────┤
│ Install              │ brew install     │ pip install        │ brew install       │
│                      │ ollama           │ llama-cpp-python   │ llama.cpp          │
├──────────────────────┼──────────────────┼────────────────────┼────────────────────┤
│ Process model        │ External daemon  │ In-process (C lib  │ Managed subprocess │
│                      │ (always-on)      │ via Python FFI)    │ (on-demand)        │
├──────────────────────┼──────────────────┼────────────────────┼────────────────────┤
│ API style            │ ollama Python    │ Direct ctypes      │ OpenAI-compatible  │
│                      │ SDK              │ calls              │ HTTP (localhost)   │
├──────────────────────┼──────────────────┼────────────────────┼────────────────────┤
│ Build dependency     │ None (prebuilt)  │ C/C++ compiler     │ None (prebuilt     │
│                      │                  │ required           │ binary)            │
├──────────────────────┼──────────────────┼────────────────────┼────────────────────┤
│ Reasoning control    │ N/A              │ Regex stripping    │ --reasoning-format │
│                      │                  │ of <think> tags    │ deepseek (native)  │
├──────────────────────┼──────────────────┼────────────────────┼────────────────────┤
│ Structured JSON      │ ollama format    │ Grammar-based      │ json_schema via    │
│                      │ param            │ decoding           │ response_format    │
├──────────────────────┼──────────────────┼────────────────────┼────────────────────┤
│ GPU acceleration     │ Via Ollama       │ Metal via ctypes   │ Metal via          │
│                      │                  │                    │ llama-server       │
├──────────────────────┼──────────────────┼────────────────────┼────────────────────┤
│ RAM overhead         │ ~1.5GB daemon    │ Model only         │ Model only         │
│                      │ + model          │ (~1.2GB)           │ (~1.2GB)           │
├──────────────────────┼──────────────────┼────────────────────┼────────────────────┤
│ Python dependency    │ ollama>=0.6.1    │ llama-cpp-python   │ openai + httpx     │
│                      │                  │ >=0.3.8            │ (pure Python)      │
├──────────────────────┼──────────────────┼────────────────────┼────────────────────┤
│ Status               │ Removed          │ Removed            │ ✅ Current         │
└──────────────────────┴──────────────────┴────────────────────┴────────────────────┘
```

---

## 2. Generation 1: Ollama Daemon

### How it worked

```
┌─────────────┐          ┌───────────────────────────┐
│  Our Python  │  HTTP    │  Ollama Daemon (separate   │
│  process     │ ──────►  │  always-on process)         │
│              │          │                             │
│  ollama SDK  │  ◄────── │  Models in ~/.ollama/       │
└─────────────┘          └───────────────────────────┘
     pip install ollama         brew install ollama
                                ollama pull qwen3:1.7b
                                ollama serve  ← must be running
```

### Why we moved away

1. **User friction**: Students had to install Ollama separately, pull a model, and keep the daemon running. If they forgot `ollama serve`, the pipeline crashed with a connection error.
2. **RAM waste**: The Ollama daemon consumed ~1.5GB even when idle, on top of the model memory. On an 8GB MacBook Air, this was significant.
3. **No structured output control**: Limited grammar-constrained decoding for JSON schema adherence.

---

## 3. Generation 2: llama-cpp-python (Embedded)

### How it worked

```
┌────────────────────────────────────────────────┐
│  Our Python process                             │
│                                                 │
│  ┌───────────────────────────────────────────┐  │
│  │  llama-cpp-python (C library via ctypes)  │  │
│  │                                           │  │
│  │  • Model loaded into process memory       │  │
│  │  • Direct function calls (no HTTP)        │  │
│  │  • Grammar-based JSON constrained decode  │  │
│  └───────────────────────────────────────────┘  │
│                                                 │
│  Models in ~/.artifactminer/models/             │
│  Auto-downloaded from HuggingFace on first run  │
└────────────────────────────────────────────────┘
     pip install llama-cpp-python  ← requires C compiler
```

### What it solved

- No daemon — model loads on-demand, unloads when done
- Auto-download models from HuggingFace (zero manual setup)
- Grammar-based constrained decoding for structured JSON output
- ~1.5GB less RAM than Ollama (no daemon overhead)

### Why we moved away

1. **Build dependency**: `llama-cpp-python` compiles C++ code during `pip install`. This required Xcode Command Line Tools and frequently failed with cryptic build errors on student machines.
2. **Reasoning tag pollution**: Qwen3 models emit `<think>...</think>` reasoning blocks. We had to regex-strip these from output — fragile and error-prone when tags were incomplete or nested.
3. **Version coupling**: Every llama.cpp upstream update required a matching llama-cpp-python release. Version mismatches caused silent inference quality regressions.

---

## 4. Generation 3: llama-server (Current)

### How it works

```
┌──────────────────────┐        ┌───────────────────────────────┐
│  Our Python process   │  HTTP  │  llama-server subprocess       │
│                       │  :PORT │  (managed by our code)         │
│  ┌─────────────────┐  │        │                                │
│  │  OpenAI Python   │  │        │  ┌──────────────────────────┐  │
│  │  SDK             │ ──────►  │  │  llama.cpp C++ engine    │  │
│  │                  │  │        │  │                          │  │
│  │  • chat.compl..  │  ◄────── │  │  • Metal GPU offload     │  │
│  │  • json_schema   │  │        │  │  • --reasoning-format    │  │
│  │  • temperature   │  │        │  │     deepseek             │  │
│  └─────────────────┘  │        │  │  • json_schema grammar   │  │
│                       │        │  └──────────────────────────┘  │
│  Pure Python deps:    │        │                                │
│  openai + httpx       │        │  Binary: brew install llama.cpp│
└──────────────────────┘        └───────────────────────────────┘
                                        ▲
                                        │  manages lifecycle
                                        │  (start/stop/restart)
                                ┌───────┴───────┐
                                │ llm_client.py  │
                                └───────────────┘
```

### Server lifecycle management

Our `llm_client.py` manages the llama-server process transparently:

```
                    generate_resume() called
                            │
                            ▼
                ┌───────────────────────┐
                │ _ensure_server_running │
                │ (model="qwen3-1.7b") │
                └───────┬───────────────┘
                        │
               ┌────────┴────────┐
               │ Server running  │
               │ with right      │───── Yes ────► Use existing server
               │ model?          │
               └────────┬────────┘
                        │ No
                        ▼
               ┌─────────────────┐
               │ Server running  │
               │ with wrong      │───── Yes ────► _restart_server()
               │ model?          │                (stop + start)
               └────────┬────────┘
                        │ No
                        ▼
               ┌─────────────────┐
               │ _start_server() │
               │                 │
               │ 1. Find binary  │──► which llama-server
               │ 2. Resolve GGUF │──► ~/.artifactminer/models/
               │ 3. Pick port    │──► OS-assigned ephemeral
               │ 4. Spawn proc   │──► subprocess.Popen(...)
               │ 5. Wait healthy │──► poll /health until 200
               └────────┬────────┘
                        │
                        ▼
               ┌─────────────────┐
               │ Server ready    │
               │ on 127.0.0.1:   │
               │ {port}          │
               └────────┬────────┘
                        │
                        ▼
               ┌─────────────────┐
               │ atexit.register │──► _stop_server() on Python exit
               │ (_stop_server)  │
               └─────────────────┘
```

### What it solved

| Problem with Gen 2 | How Gen 3 fixes it |
|---|---|
| C++ build dependency during `pip install` | Pre-built binary via `brew install llama.cpp` |
| Regex stripping `<think>` tags | `--reasoning-format deepseek` separates thinking into `reasoning_content` field natively |
| Version coupling with llama-cpp-python | Direct use of llama.cpp binary — update with `brew upgrade` |
| Python dependencies with C extensions | Pure Python deps only: `openai` + `httpx` |

### Launch command anatomy

```bash
llama-server \
    --model ~/.artifactminer/models/Qwen_Qwen3-1.7B-Q4_K_M.gguf \
    --ctx-size 8192 \           # context window (from MODEL_REGISTRY)
    --n-gpu-layers -1 \         # Metal: offload ALL layers to GPU
    --port 52431 \              # OS-assigned ephemeral port
    --reasoning-format deepseek \ # native <think> separation
    --log-disable               # suppress server logs
```

### Dependency change (pyproject.toml)

```
Gen 1:  "ollama>=0.4.0"

Gen 2:  "llama-cpp-python>=0.3.8",
        "huggingface-hub>=0.24"

Gen 3:  "huggingface-hub>=0.24"      ← model auto-download only
        (+ brew install llama.cpp)     ← system binary, not Python dep
```

The Python-side deps are now `openai` (for the OpenAI-compatible client) and `httpx` (for health-check polling) — both pure Python, no C compilation.

---

## 5. Architecture Deep Dive

### Full pipeline flow (current state)

```
┌──────────────────────────────────────────────────────────────────────────┐
│                         User uploads ZIP                                  │
└────────────────────────────────┬─────────────────────────────────────────┘
                                 │
                                 ▼
┌──────────────────────────────────────────────────────────────────────────┐
│  PHASE 1: Extract & Discover                                              │
│                                                                           │
│  extract_zip() ──► discover_git_repos()                                   │
│  Result: List of repo paths                                               │
└────────────────────────────────┬─────────────────────────────────────────┘
                                 │
                                 ▼
┌──────────────────────────────────────────────────────────────────────────┐
│  PHASE 2: Per-Repo Static Analysis (EXISTING)                             │
│                                                                           │
│  For each repo:                                                           │
│    getRepoStats()       → languages, frameworks, health score             │
│    getUserRepoStats()   → contribution %, commit frequency                │
│    DeepRepoAnalyzer()   → skills, insights, evidence                      │
│    collect_user_additions() → code additions text                         │
│                                                                           │
│  Output: Raw analysis objects                                             │
└────────────────────────────────┬─────────────────────────────────────────┘
                                 │
                                 ▼
┌──────────────────────────────────────────────────────────────────────────┐
│  PHASE 3: Per-Repo LLM-Enhanced Analysis (NEW)                            │
│                                                                           │
│  For each repo:                                                           │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │  3a. build_project_facts()     → ProjectFacts bundle (pure data)   │  │
│  │                                                                     │  │
│  │  3b. extract_commit_messages() → List[CommitInfo]        (static)  │  │
│  │      classify_commits()        → {"feature": 15, ...}    [LLM #1] │  │
│  │                                                                     │  │
│  │  3c. compute_skill_first_appearances() → skill dates     (static)  │  │
│  │                                                                     │  │
│  │  3d. compute_style_metrics()   → StyleMetrics            (static)  │  │
│  │                                                                     │  │
│  │  3e. compute_complexity_metrics() → [FileComplexity]     (static)  │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
│                                                                           │
│  Note: Only step 3b uses the LLM. Steps 3c-3e are pure static analysis.  │
│  The LLM call count = 1 per repo (commit classification only).            │
└────────────────────────────────┬─────────────────────────────────────────┘
                                 │
                                 ▼
┌──────────────────────────────────────────────────────────────────────────┐
│  PHASE 4: Portfolio Aggregation                                           │
│                                                                           │
│  build_portfolio_facts()                                                  │
│    • Deduplicates skills across projects                                  │
│    • Aggregates commit breakdowns                                         │
│    • Merges skill timelines (sorted by date)                              │
│    • Finds date range (earliest → latest commit)                          │
│                                                                           │
│  Output: PortfolioFacts (pure data, no LLM)                               │
└────────────────────────────────┬─────────────────────────────────────────┘
                                 │
                                 ▼
┌──────────────────────────────────────────────────────────────────────────┐
│  PHASE 5: Portfolio-Level LLM Narratives                                  │
│                                                                           │
│  5a. generate_skill_timeline_narrative()  → "Adopted Python in 2023..."   │
│       Input: chronological skill appearances           [LLM #2]           │
│                                                                           │
│  5b. generate_style_fingerprint()         → "Writes concise functions..." │
│       Input: aggregated style metrics                  [LLM #3]           │
│                                                                           │
│  5c. generate_complexity_narrative()      → "Handles complex logic..."    │
│       Input: complexity metrics                        [LLM #4]           │
│                                                                           │
│  Note: All three use structured JSON output (Pydantic schema constraint)  │
└────────────────────────────────┬─────────────────────────────────────────┘
                                 │
                                 ▼
┌──────────────────────────────────────────────────────────────────────────┐
│  PHASE 6: Prose Polish (enhance.py)                                       │
│                                                                           │
│  For each project:                                                        │
│    build_project_prompt() → 3-5 bullet points          [LLM #5..N]       │
│                                                                           │
│  Once for portfolio:                                                      │
│    build_portfolio_prompt() → summary + skills section  [LLM #N+1]        │
│                                                                           │
│  Note: These use free-form text output (not JSON-constrained)             │
└────────────────────────────────┬─────────────────────────────────────────┘
                                 │
                                 ▼
┌──────────────────────────────────────────────────────────────────────────┐
│  PHASE 7: Output                                                          │
│                                                                           │
│  GenerationResult.to_json()      → resume_output.json                     │
│  GenerationResult.to_markdown()  → resume_output.md                       │
│                                                                           │
│  Sections: Summary, Skills, Projects (bullets), Skill Evolution,          │
│            Developer Profile, Complexity Highlights, Work Breakdown        │
└──────────────────────────────────────────────────────────────────────────┘
```

### LLM call budget

For a portfolio with **N** projects, the pipeline makes:

```
  1 × commit classification per repo     =  N calls   (structured JSON)
  1 × skill timeline narrative            =  1 call    (structured JSON)
  1 × developer style fingerprint         =  1 call    (structured JSON)
  1 × complexity narrative                =  1 call    (structured JSON)
  1 × project bullets per repo            =  N calls   (free text)
  1 × portfolio summary + skills          =  1 call    (free text)
  ─────────────────────────────────────────────────────
  Total                                   = 2N + 4 calls

  For 8 projects: 2(8) + 4 = 20 calls
```

### Data flow: what the LLM sees vs what it never sees

```
  ┌──────────────────────┐       ┌──────────────────────────────┐
  │  RAW DATA             │       │  WHAT THE LLM RECEIVES        │
  │  (never sent to LLM)  │       │  (pre-digested facts only)    │
  ├──────────────────────┤       ├──────────────────────────────┤
  │  Source code files    │ ───►  │  "Stack: Python (67%)"        │
  │  Git blob diffs       │       │  "Contribution: 100%"         │
  │  File contents        │       │  "Skills: FastAPI, pytest"    │
  │  AST nodes            │       │  "Commit: feat: add alerts"   │
  │  Dependency manifests │       │  "Avg function length: 12"    │
  │  Raw git objects      │       │  "Cyclomatic complexity: 3.9" │
  └──────────────────────┘       └──────────────────────────────┘

  The LLM is a prose writer, not a code analyzer.
  All analysis is done by static analysis before the LLM is called.
```

---

## 6. Model Management

### Model registry

Defined in `llm_client.py`:

```python
MODEL_REGISTRY: dict[str, tuple[str, str, int]] = {
    #  friendly_name: (hf_repo_id, gguf_filename, context_length)
    "qwen3-1.7b": (
        "bartowski/Qwen_Qwen3-1.7B-GGUF",
        "Qwen_Qwen3-1.7B-Q4_K_M.gguf",
        8192,
    ),
    "lfm2.5-1.2b": (
        "LiquidAI/LFM2.5-1.2B-Instruct-GGUF",
        "LFM2.5-1.2B-Instruct-Q4_K_M.gguf",
        8192,
    ),
    "qwen2.5-coder-3b": (
        "Qwen/Qwen2.5-Coder-3B-Instruct-GGUF",
        "qwen2.5-coder-3b-instruct-q6_k.gguf",
        16384,
    ),
}
```

### Model resolution flow

```
  User passes: "qwen3-1.7b"
         │
         ▼
  ┌──────────────────────┐
  │ Ends with .gguf?     │──── Yes ────► Direct file path
  └──────┬───────────────┘
         │ No
         ▼
  ┌──────────────────────┐
  │ In MODEL_REGISTRY?   │──── Yes ────► ~/.artifactminer/models/{filename}
  └──────┬───────────────┘
         │ No
         ▼
  ┌──────────────────────┐
  │ File exists in       │──── Yes ────► ~/.artifactminer/models/{name}
  │ models dir?          │
  └──────┬───────────────┘
         │ No
         ▼
  FileNotFoundError with helpful message
```

### Auto-download flow

```
  ensure_model_available("qwen3-1.7b")
         │
         ▼
  ┌──────────────────────┐
  │ GGUF file exists     │──── Yes ────► Return (nothing to do)
  │ on disk?             │
  └──────┬───────────────┘
         │ No
         ▼
  ┌──────────────────────┐
  │ In MODEL_REGISTRY?   │──── No ─────► RuntimeError
  └──────┬───────────────┘
         │ Yes
         ▼
  ┌──────────────────────┐
  │ hf_hub_download()    │
  │                      │
  │ repo: bartowski/...  │
  │ file: ...Q4_K_M.gguf │
  │ dest: ~/.artifact... │
  └──────────────────────┘
         │
         ▼
  Model ready on disk (~1.2GB one-time download)
```

### GPU detection

```python
def _get_gpu_layers() -> int:
    if platform.system() == "Darwin" and platform.machine() == "arm64":
        return -1   # Metal: offload ALL layers
    return 0        # CPU-only on other platforms
```

On Apple Silicon: `-ngl -1` tells llama-server to offload every transformer layer to the Metal GPU. This is critical for performance — CPU-only inference is ~5x slower.

---

## 7. Inference Call Types

The pipeline uses two distinct inference modes, both served by the same llama-server instance:

### Free-text mode (resume bullets, portfolio summary)

```
┌──────────────────────────────────────────────────────────┐
│  query_llm_text()                                         │
│                                                           │
│  Request:                                                 │
│    POST /v1/chat/completions                              │
│    {                                                      │
│      "model": "local",                                    │
│      "messages": [                                        │
│        {"role": "system", "content": SYSTEM_CONTEXT},     │
│        {"role": "user", "content": project_prompt}        │
│      ],                                                   │
│      "temperature": 0.3,                                  │
│      "max_tokens": 4096                                   │
│    }                                                      │
│                                                           │
│  Response:                                                │
│    choices[0].message.content  ← clean text               │
│    (reasoning_content holds <think> separately)            │
└──────────────────────────────────────────────────────────┘
```

### Structured JSON mode (commit classification, narratives)

```
┌──────────────────────────────────────────────────────────┐
│  query_llm()                                              │
│                                                           │
│  Request:                                                 │
│    POST /v1/chat/completions                              │
│    {                                                      │
│      "model": "local",                                    │
│      "messages": [...],                                   │
│      "temperature": 0.1,                                  │
│      "response_format": {                                 │
│        "type": "json_schema",                             │
│        "json_schema": {                                   │
│          "name": "CommitClassificationBatch",             │
│          "schema": { ... Pydantic JSON schema ... }       │
│        }                                                  │
│      }                                                    │
│    }                                                      │
│                                                           │
│  Response:                                                │
│    choices[0].message.content  ← valid JSON               │
│    Parsed via: schema.model_validate_json(content)        │
│                                                           │
│  The json_schema response_format uses llama.cpp's         │
│  grammar-based constrained decoding — the model is        │
│  physically unable to emit invalid JSON.                  │
└──────────────────────────────────────────────────────────┘
```

### Reasoning mode handling across generations

```
  Gen 2 (llama-cpp-python):
  ┌─────────────────────────────────────────────────┐
  │  Model output:                                   │
  │  "<think>Let me analyze...</think>              │
  │   • Implemented REST endpoint..."               │
  │                                                  │
  │  Our code: regex strip <think>...</think>        │
  │  Problem:  fragile, breaks on nested/incomplete  │
  └─────────────────────────────────────────────────┘

  Gen 3 (llama-server):
  ┌─────────────────────────────────────────────────┐
  │  Server flag: --reasoning-format deepseek        │
  │                                                  │
  │  Response JSON:                                  │
  │  {                                               │
  │    "choices": [{                                 │
  │      "message": {                                │
  │        "reasoning_content": "Let me analyze...", │  ← thinking here
  │        "content": "• Implemented REST endpoint"  │  ← clean output
  │      }                                           │
  │    }]                                            │
  │  }                                               │
  │                                                  │
  │  Our code: just read .content — no stripping     │
  └─────────────────────────────────────────────────┘
```

---

## 8. Prompt Hardening Journey

After the infrastructure was stable, we found two categories of LLM output quality issues through end-to-end testing with real student portfolios (8 projects).

### Issue 1: Verbatim example copying

**Symptom**: Every project's first bullet was "Implemented REST alerting endpoint and JSON export for test results" — including projects with no REST endpoints (algorithms-toolkit, infra-terraform, ml-lab-notebooks).

**Root cause**: The system prompt contained a concrete `GOOD:` example. The 3B model couldn't distinguish "this is the style to follow" from "output this text."

```
  BEFORE (enhance.py SYSTEM_CONTEXT):
  ┌─────────────────────────────────────────────────────────┐
  │  - Be SPECIFIC: reference actual features...             │
  │    GOOD: "Implemented REST alerting endpoint and         │
  │           JSON export for test results"                  │
  │    BAD:  "Built and maintained the project"              │
  │                                                          │
  │  Model behavior: copied the GOOD example verbatim        │
  │  into every project as bullet #1                         │
  └─────────────────────────────────────────────────────────┘

  AFTER:
  ┌─────────────────────────────────────────────────────────┐
  │  - Be SPECIFIC: reference actual features...             │
  │    Do NOT use generic phrases like "built and            │
  │    maintained the project". Instead, name the concrete   │
  │    thing that was built, using the commit messages       │
  │    as your source.                                       │
  │                                                          │
  │  Fix: describe the style abstractly, no concrete         │
  │  example for the model to parrot                         │
  └─────────────────────────────────────────────────────────┘
```

**Lesson**: Small models (<7B) treat concrete examples as content to reproduce. Use abstract style descriptions instead.

### Issue 2: Cross-project hallucination

**Symptom**: `algorithms-toolkit` (a pure Python algorithms library) had a bullet claiming a "REST alerting endpoint" — a feature from `sensor-fleet-backend` bleeding through.

**Root cause**: The prompt said "drawn ONLY from the provided facts" but the model treated skills metadata as equally valid source material as commit messages. Skills data spans project boundaries.

```
  BEFORE:
  ┌─────────────────────────────────────────────────────────┐
  │  Rules:                                                  │
  │  - Each bullet: factual, drawn ONLY from provided facts  │
  │                                                          │
  │  Problem: "Skills demonstrated: REST API Design" is also │
  │  a "fact" — model invents a REST endpoint to match it    │
  └─────────────────────────────────────────────────────────┘

  AFTER:
  ┌─────────────────────────────────────────────────────────┐
  │  Rules:                                                  │
  │  - EVERY bullet must trace back to a specific commit     │
  │    message listed below. Do NOT invent features from     │
  │    the "Skills demonstrated" or "Key insights" sections. │
  │    If fewer than 3 commit messages exist, write fewer    │
  │    bullets — never fabricate.                             │
  │                                                          │
  │  + After {context}:                                      │
  │  CRITICAL: Only reference features that appear in the    │
  │  "What this developer built" commit messages above.      │
  │                                                          │
  │  Fix: narrow source of truth from "all facts" → "commit  │
  │  messages only" — concrete, auditable                    │
  └─────────────────────────────────────────────────────────┘
```

### Issue 3: Skills taxonomy duplicates

**Symptom**: "TypeScript" appeared in both Languages AND Frameworks & Libraries.

**Root cause**: The portfolio prompt fed the model three overlapping lists (Languages, Frameworks, Top Skills) and told it to "Group skills into categories" without a dedup constraint.

```
  BEFORE:
  ┌─────────────────────────────────────────────────────────┐
  │  IMPORTANT rules for the SKILLS section:                 │
  │  - Group skills into categories                          │
  │  - List ONLY skill names separated by commas             │
  └─────────────────────────────────────────────────────────┘

  AFTER:
  ┌─────────────────────────────────────────────────────────┐
  │  IMPORTANT rules for the SKILLS section:                 │
  │  - Group skills into categories                          │
  │  - Each skill must appear in EXACTLY ONE category.       │
  │    If a skill could fit multiple categories, place it    │
  │    in the most specific one                              │
  │  - Never list a programming language under Frameworks    │
  │  - List ONLY skill names separated by commas             │
  └─────────────────────────────────────────────────────────┘
```

---

## 9. Files Reference

### Core LLM infrastructure

| File | Purpose |
|------|---------|
| `src/artifactminer/resume/llm_client.py` | Server lifecycle, model registry, inference (text + JSON) |
| `src/artifactminer/resume/enhance.py` | Prompt construction, bullet generation, portfolio summary |
| `src/artifactminer/resume/facts.py` | ProjectFacts / PortfolioFacts data structures, `to_llm_context()` |
| `src/artifactminer/resume/generate.py` | Pipeline orchestrator — phases 1-7 |
| `src/artifactminer/resume/cli.py` | CLI: `resume generate`, `resume download-model`, `resume benchmark` |

### Analysis subpackage

| File | Static analysis | LLM call | Output type |
|------|----------------|----------|-------------|
| `analysis/commit_classifier.py` | Extract commit messages from git | Classify as feature/bugfix/... | `Dict[str, int]` |
| `analysis/skill_timeline.py` | Find skill first-appearance dates | Generate growth narrative | `SkillTimelineNarrative` (JSON) |
| `analysis/developer_style.py` | Compute function length, naming, type hints | Generate developer profile | `DeveloperFingerprint` (JSON) |
| `analysis/complexity_narrative.py` | Compute cyclomatic complexity, nesting | Generate complexity narrative | `ComplexityNarrative` (JSON) |

---

## Appendix: Evaluated Models

| Model | Size | Quantization | Tested? | Verdict |
|-------|------|-------------|---------|---------|
| **Qwen3 1.7B** | 1.7B | Q4_K_M | Yes | Good JSON, poor instruction following (hallucination, skill duplication) |
| **LFM2.5 1.2B** | 1.2B | Q4_K_M | Registered | Authors say "not recommended for programming" |
| **Qwen2.5-Coder 3B** | 3B | Q6_K | Yes | Better instruction following, but copies prompt examples verbatim |

A separate model research effort is underway — see `llm_model_research_brief.md` for the full evaluation criteria and candidate list.
