# LLM Infrastructure Evolution

This document explains how the local LLM stack evolved and why the current approach exists.

## Executive view

Evolution map:

Generation 1 (legacy external daemon runtime)
-> Generation 2 (embedded llama-cpp-python)
-> Generation 3 (llama-server subprocess + OpenAI SDK)

Primary lesson: operational reliability and setup simplicity matter as much as model quality.

## Generation 1: legacy external daemon runtime

How it behaved:

- Required an always-on external daemon.
- Model lifecycle was opaque from application code.
- Startup and idle-memory overhead were painful on constrained laptops.

Why we moved on:

- Harder local UX for occasional use.
- Less control over process lifecycle in the app.

## Generation 2: Embedded llama-cpp-python

What improved:

- No external daemon.
- Direct in-process calls.

Why it still hurt in practice:

- Build dependencies and platform-specific compilation complexity.
- Team setup inconsistency across machines.
- More CI friction due to native extension requirements.

## Generation 3: llama-server + OpenAI SDK

Current architecture:

Application process
-> starts `llama-server` when needed
-> calls OpenAI-compatible endpoint locally
-> validates responses
-> shuts down server cleanly

Why this is the current default:

- Clear lifecycle control in our code.
- Process isolation reduces blast radius from model/runtime issues.
- Standard client interface via OpenAI SDK.
- Simpler onboarding than native compile-heavy paths.

## Model management policy

Current policy map:

Known model alias
-> resolve expected GGUF filename
-> check local file in `~/.artifactminer/models/`
-> run if present, fail with guidance if absent

Important note:

- We do not auto-download models.
- The system returns actionable manual-download instructions.

## Runtime lifecycle behavior

Request lifecycle diagram:

Generate request
-> resolve model path
-> choose free local port
-> spawn server
-> wait for health
-> run LLM queries
-> teardown on completion or exit

## Trade-off summary

Strengths of current stack:

- Better operational predictability.
- Cleaner separation between app logic and inference engine.
- Easier local debugging through explicit process state.

Remaining costs:

- External binary installation still required.
- Cold starts still exist.
- Throughput depends on local hardware and chosen model.

## What we are optimizing next

Roadmap map:

Prompt and context efficiency
-> safer retries and partial-failure behavior
-> caching repeated LLM outputs
-> stronger end-to-end tests with mocked inference
