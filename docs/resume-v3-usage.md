# Resume v3 Usage Guide

This guide explains how to use the resume v3 pipeline in plain language. It is intentionally short and practical.

## What v3 does

Resume v3 generates resume content from a ZIP of Git repositories by combining static repo analysis with local LLM reasoning.

Flow map:

ZIP file -> Repository discovery -> EXTRACT signals -> QUERY with LLM -> ASSEMBLE outputs -> `resume.md` and `resume.json`

## Before you run it

- Install `llama-server` from llama.cpp.
- Put at least one GGUF model in `~/.artifactminer/models/`.
- Confirm your model name matches a registry alias or pass a direct `.gguf` path.
- Make sure you know the email used in your git commits.

Model setup map:

Choose model on HuggingFace -> Download GGUF -> Move to `~/.artifactminer/models/` -> Verify with `artifactminer resume check-models`

## Typical run experience

When you run `artifactminer resume generate`, the system usually does this sequence:

1. Validates the ZIP and user email.
2. Confirms the model file exists locally.
3. Starts `llama-server` if needed.
4. Extracts metadata from each repository.
5. Runs project and portfolio LLM queries.
6. Assembles Markdown and JSON outputs.
7. Stops server resources when done.

Execution map:

Input validation -> Model check -> Server health -> Extractors -> LLM queries -> Output assembly -> Complete

## Outputs you should expect

- `resume.md`: readable resume draft for humans.
- `resume.json`: structured output for APIs, UI rendering, or downstream tooling.

The content focuses on:

- Project impact and scope.
- Skills inferred from code and commit history.
- Portfolio-level themes across repositories.

## How to validate quality quickly

- Confirm each project has clear, concrete bullets.
- Check that technical skills match real repository evidence.
- Ensure no duplicate sections or empty placeholder text.
- Compare v2 and v3 output for the same input ZIP.

Quality checklist map:

Correctness -> Specificity -> Coverage -> Readability -> Consistency

## Common problems and fixes

Model not found:

- Cause: missing GGUF file or wrong model alias.
- Fix: place the GGUF in `~/.artifactminer/models/` or pass a direct model path.

No meaningful project output:

- Cause: ZIP has no git repos, or email does not match commit authorship.
- Fix: verify repository content and use the exact git email for attribution.

Slow generation:

- Cause: cold model start, larger projects, or slower hardware.
- Fix: run smaller batches during iteration and keep model choice lightweight.

## Team review focus

If you are reviewing this pipeline, the highest-value feedback areas are:

- Extractor usefulness: which metadata is most resume-relevant.
- Prompt contract: where strict JSON helps or hurts quality.
- Failure strategy: partial outputs vs all-or-nothing behavior.
- Evaluation method: lightweight rubric for v2 vs v3 comparison.
