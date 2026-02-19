# LLM Design History

This is a historical design note. It captures the intent behind the earlier llama-cpp-focused direction and how those ideas informed the current v3 pipeline.

## Original proposal intent

The proposal aimed to increase resume quality by combining static repository analysis with targeted LLM reasoning instead of relying on prose-only rewriting.

Concept map:

Static metrics first
-> compact LLM prompts over structured facts
-> resume-ready narratives

## What was valuable from that phase

- The static-first, LLM-light mindset remains valid.
- Per-feature analysis modules made experimentation fast.
- Structured outputs improved downstream composability.

## What changed since then

The infrastructure moved away from embedded llama-cpp integration toward `llama-server` subprocess management with an OpenAI-compatible client.

Reason map:

Native build friction across environments
-> setup inconsistency for teammates
-> operational overhead
-> preference for process-isolated runtime

## Current stance

This proposal is no longer the implementation plan, but it is still useful as context for why the project prioritizes:

- Structured metadata before inference.
- Modular analysis boundaries.
- Local-first operation with explicit model control.

## How to use this document now

Treat it as a design history artifact, not a runbook.

For active implementation details, use:

- `docs/resume-v3-architecture.md` for architecture.
- `docs/resume-v3-usage.md` for usage flow.
- `docs/llm-runtime-evolution.md` for runtime decisions.
