# Resume v3 Architecture

This document describes the architecture and behavior of the resume v3 pipeline using diagrams and natural language.

## Design goals

- Improve resume quality by sending structured context instead of raw code.
- Keep local inference manageable on student hardware.
- Make each stage testable and failure-aware.

## End-to-end architecture

System diagram:

ZIP input
-> Repo discovery
-> EXTRACT phase (no LLM)
-> `ProjectDataBundle`
-> QUERY phase (LLM calls)
-> `PortfolioDataBundle`
-> ASSEMBLE phase
-> Markdown + JSON outputs

## Phase 1: EXTRACT

Purpose: gather deterministic, low-cost repository signals before any LLM call.

Extractor map:

README extractor + Commit extractor + Structure extractor + Constructs extractor + Project-type classifier
-> merged into `ProjectDataBundle`

What each extractor contributes:

- README: project intent, feature hints, technology references.
- Commits: activity timeline and change categories.
- Structure: directory layout, language distribution, framework signals.
- Constructs: function, class, and import-level structural hints.
- Project type: broad category such as app, library, or tool.

## Phase 2: QUERY

Purpose: use the LLM as an analyst over structured metadata, not as a raw parser.

Query map:

Per-project prompts (one call per project)
+
Portfolio prompts (three calls total)
-> merged into `PortfolioDataBundle`

Expected outcomes:

- Clear project-level impact and complexity framing.
- Skills and growth themes across repositories.
- More coherent portfolio narrative than single-shot prompting.

## Phase 3: ASSEMBLE

Purpose: convert extracted facts and LLM analysis into stable output formats.

Assembly map:

`ProjectDataBundle` + `PortfolioDataBundle`
-> formatter and schema mapper
-> `resume.md` and `resume.json`

Behavior:

- Produces human-readable markdown.
- Produces machine-readable JSON for downstream systems.
- Handles missing fields with graceful defaults.

## LLM runtime model

The pipeline uses `llama-server` as a subprocess and the OpenAI Python SDK as the client interface.

Lifecycle diagram:

Generation request
-> model file resolution
-> start server on free port
-> health check loop
-> run queries
-> stop server on completion or process exit

Model policy:

- No auto-download behavior.
- GGUF files are manually managed in `~/.artifactminer/models/`.
- Errors include actionable links for manual model acquisition.

## Data contracts

Type flow diagram:

Raw repo signals -> `ProjectDataBundle`
-> query outputs -> `PortfolioDataBundle`
-> final packaging -> `ResumeOutput`

Why this matters:

- Easier testing at each stage.
- Fewer shape mismatches between components.
- Safer refactors as extractors evolve.

## Failure strategy

Failure handling map:

Local extractor failure -> explicit error or safe omission (context-dependent)
LLM response issue -> retry logic and validation
Model missing -> immediate actionable runtime error

Current direction:

- Prefer informative failures over silent corruption.
- Keep partial progress where output integrity remains acceptable.

## Performance profile

Where time is typically spent:

Extraction cost (repo size dependent)
+
LLM inference cost (model and prompt dependent)
>
assembly cost (small)

Optimization levers:

- Cache stable LLM results.
- Parallelize safe extraction work.
- Reduce prompt payload while preserving signal quality.

## Testing strategy

Test layers:

Unit tests for extractors and prompts
-> integration tests for pipeline wiring
-> end-to-end tests with mock LLM for deterministic CI

Current state:

- Unit coverage exists for key v3 modules.
- End-to-end mock-based validation is the next priority.

## Review questions for the team

- Which extractor improvements will most improve resume usefulness?
- Should we formalize a stable extractor JSON schema now?
- Where should strict JSON output be mandatory vs optional?
- What is the best default failure mode for local users?
- Which quality rubric should define v3 success vs v2?
