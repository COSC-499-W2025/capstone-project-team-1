# Local LLM Runtime Migration Guide

This document defines the runtime work needed to move Artifact Miner toward a fully local `llama-server`-based LLM path on `development`.

It is written to be forwarded directly to teammates who will implement the runtime work.

## Goal

Build a reusable local LLM runtime for the whole application.

The runtime must:

- run fully locally after install
- use `llama-server` as the only local inference backend
- support local model aliases and direct `.gguf` paths
- provide one stable inference interface for the rest of the app
- remove feature modules from needing to know about Ollama, cloud OpenAI, or subprocess details

The runtime must not:

- contain resume-specific logic
- contain API route logic
- contain frontend logic
- contain project-analysis business logic
- silently fall back to cloud providers

## Product Rule

Artifact Miner is local-first.

Normal LLM operation must not require internet access.

That means:

- no hidden cloud fallback
- no auto-download of models
- no provider-specific logic scattered across feature code
- all local model execution goes through one shared runtime package

## Current State On `origin/development`

The current `development` line does not have a unified local runtime.

LLM logic is scattered across:

- `src/artifactminer/helpers/ollama.py`
- `src/artifactminer/helpers/openai.py`
- `src/artifactminer/RepositoryIntelligence/repo_intelligence_AI.py`
- `src/artifactminer/api/openai.py`

This is the main problem:

- feature code chooses providers directly
- cloud and local paths are mixed together
- there is no app-wide runtime abstraction
- there is no single place to own model lifecycle

## Target Location

The new runtime must live here:

- `src/artifactminer/llm/`
- `src/artifactminer/llm/runtime/`

Do not put the runtime under:

- `src/artifactminer/resume/`
- `src/artifactminer/helpers/`
- `src/artifactminer/api/`

Why:

- this is infrastructure for the whole app
- it should be reusable by Repository Intelligence, resume generation, and future local features
- it should not look feature-specific

## Target Package Layout

Create this package structure:

```text
src/artifactminer/llm/
  __init__.py
  client.py
  models.py
  runtime/
    __init__.py
    config.py
    errors.py
    registry.py
    process_manager.py
    health.py
    inference.py
```

## Layer Responsibilities

### `artifactminer.llm.client`

Public import point for the rest of the app.

Everything outside the runtime should depend on this file.

This file should expose a small stable interface such as:

- `ensure_model_available(model: str) -> None`
- `check_model_available(model: str) -> bool`
- `list_available_models() -> list[str]`
- `query_text(...) -> str`
- `query_json(...) -> T`
- `unload_model() -> None`
- `runtime_status() -> dict`

### `artifactminer.llm.models`

Shared typed models and option containers.

Examples:

- `InferenceOptions`
- `RuntimeStatus`
- `ModelDescriptor`

Keep these generic and runtime-focused.

### `artifactminer.llm.runtime.registry`

Owns model alias and file resolution.

This module should:

- define supported model aliases
- map aliases to GGUF filenames
- map aliases to context lengths
- resolve direct `.gguf` paths
- validate model existence
- list locally available models

This module should not:

- start subprocesses
- call the model
- know about app features

### `artifactminer.llm.runtime.process_manager`

Owns `llama-server` process lifecycle.

This module should:

- find `llama-server` on `PATH`
- choose a free local port
- start the server
- stop the server
- restart the server for a different model
- reuse an already running server if the same model is loaded
- keep track of server state

This module should not:

- parse app prompts
- validate JSON output
- know about FastAPI routes

### `artifactminer.llm.runtime.health`

Owns health-check logic only.

This module should:

- poll the local `llama-server` health endpoint
- fail with timeout if the server never becomes healthy
- provide a small helper used by the process manager

### `artifactminer.llm.runtime.inference`

Owns request/response logic for the local server.

This module should:

- create the OpenAI-compatible client pointing to the local server
- implement plain text inference
- implement structured JSON inference
- support grammar-constrained generation
- apply per-model defaults like temperature or `top_p`
- normalize bad/empty output into typed runtime errors

This module should not:

- manage subprocess startup directly
- embed feature prompts

### `artifactminer.llm.runtime.config`

Owns runtime-level defaults and local execution settings.

This module should contain:

- models directory path
- startup timeout
- health timeout
- context window lookup helpers
- GPU layer selection policy
- default sampling presets

### `artifactminer.llm.runtime.errors`

Owns typed runtime exceptions.

At minimum define:

- `LocalLLMRuntimeError`
- `LlamaServerNotFoundError`
- `ModelNotFoundError`
- `ModelStartupTimeoutError`
- `ModelServerCrashedError`
- `InvalidLLMResponseError`

Do not return stringified error payloads from deep runtime code.

Raise typed exceptions and let callers format them.

## Dependency Rules

These rules are mandatory.

Allowed imports:

- `artifactminer.llm.client` may import from `artifactminer.llm.runtime.*`
- `artifactminer.llm.runtime.*` may import from `artifactminer.llm.models`
- feature modules may import from `artifactminer.llm.client`

Disallowed imports:

- `artifactminer.llm.runtime.*` importing from `resume/`
- `artifactminer.llm.runtime.*` importing from `api/`
- `artifactminer.llm.runtime.*` importing from `tui/`
- `artifactminer.llm.runtime.*` importing from `opentui-react-exp/`
- feature modules importing `subprocess`-level runtime internals directly

If a new feature needs local inference, it should import `artifactminer.llm.client`.

## Public Interface Contract

The rest of the app should eventually use an interface like this:

```python
from typing import TypeVar
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)

def ensure_model_available(model: str) -> None: ...
def check_model_available(model: str) -> bool: ...
def list_available_models() -> list[str]: ...

def query_text(
    prompt: str,
    *,
    model: str,
    system: str | None = None,
    grammar: str | None = None,
    temperature: float | None = None,
    max_tokens: int | None = None,
) -> str: ...

def query_json(
    prompt: str,
    schema: type[T],
    *,
    model: str,
    system: str | None = None,
    temperature: float | None = None,
) -> T: ...

def unload_model() -> None: ...
def runtime_status() -> dict: ...
```

Keep the interface small.

Do not expose raw provider-specific details unless absolutely necessary.

## Team Split

## Teammate A: `llama-server` Path Owner

This person owns server lifecycle and runtime state.

### Files Owned

- `src/artifactminer/llm/runtime/process_manager.py`
- `src/artifactminer/llm/runtime/health.py`
- `src/artifactminer/llm/runtime/config.py`
- `src/artifactminer/llm/runtime/errors.py`

### Responsibilities

- replace the old local provider path with `llama-server`
- implement binary discovery
- implement free-port selection
- implement startup and shutdown behavior
- implement restart behavior when the model changes
- implement server reuse when the same model is already running
- implement health polling and startup timeout handling
- expose enough runtime state for debugging

### Acceptance Criteria

- starting the same model twice does not start two servers
- switching models restarts cleanly
- missing `llama-server` produces a clear actionable error
- startup timeout is explicit
- server crash after startup is detectable
- runtime uses local loopback only

### Out Of Scope

- no prompt-writing logic
- no JSON schema shaping beyond runtime validation
- no resume code

## Teammate B: Model Registry And Inference Owner

This person owns model resolution and the query layer.

### Files Owned

- `src/artifactminer/llm/runtime/registry.py`
- `src/artifactminer/llm/runtime/inference.py`
- `src/artifactminer/llm/client.py`
- `src/artifactminer/llm/models.py`

### Responsibilities

- define model aliases and metadata
- resolve aliases to local GGUF files
- support direct `.gguf` paths
- implement `ensure_model_available`
- implement `check_model_available`
- implement `list_available_models`
- implement local text inference
- implement local JSON inference
- implement grammar-constrained generation
- normalize empty or malformed responses into typed errors

### Acceptance Criteria

- aliases resolve to expected local files
- direct paths work
- missing-model errors show the expected path
- text inference works against local `llama-server`
- JSON inference validates against Pydantic schema
- invalid or empty responses fail cleanly

### Out Of Scope

- no subprocess lifecycle logic
- no feature prompt definitions
- no route logic

## Shared Integration Follow-Up

After the runtime exists, other code should be rewired to use it.

The first integration targets are:

- `src/artifactminer/RepositoryIntelligence/repo_intelligence_AI.py`
- `src/artifactminer/api/openai.py`
- `src/artifactminer/helpers/ollama.py`
- `src/artifactminer/helpers/openai.py`

The long-term goal is:

- feature code imports `artifactminer.llm.client`
- only runtime code knows about `llama-server`

## PR Size Rule

Every PR should stay around 500 changed lines total.

That means:

- small enough to review in one sitting
- one concern per PR
- tests included in the same PR

Hard rule:

- do not open a 1,500+ line runtime PR

Preferred target:

- 250 to 550 changed lines per PR

If a task naturally grows beyond that, split it.

## PR Design Rules

Each PR must satisfy all of these:

- one clear purpose
- one owner
- tests included
- no unrelated formatting churn
- no moving multiple architectural layers at once
- no mixing runtime creation with large caller rewires

## Recommended PR Sequence

Follow this order.

### PR 1: Runtime Package Skeleton

Owner:

- Teammate A

Scope:

- create `src/artifactminer/llm/`
- create `src/artifactminer/llm/runtime/`
- add `__init__.py` files
- add `errors.py`
- add `models.py`
- add `config.py`

Target size:

- 250 to 400 lines

Deliverable:

- empty but typed package skeleton with shared errors and config

### PR 2: Model Registry

Owner:

- Teammate B

Scope:

- add `registry.py`
- implement alias resolution
- implement GGUF path resolution
- implement model listing and availability helpers
- add unit tests

Target size:

- 350 to 500 lines

Deliverable:

- a tested model registry independent of subprocess logic

### PR 3: Health Helpers

Owner:

- Teammate A

Scope:

- add `health.py`
- implement `/health` polling helpers
- add timeout handling
- add tests with mocks

Target size:

- 200 to 350 lines

Deliverable:

- reusable server health-check helper

### PR 4: Process Manager Start/Stop

Owner:

- Teammate A

Scope:

- add `process_manager.py`
- implement binary discovery
- implement free-port selection
- implement `start_server()`
- implement `stop_server()`
- add mocked lifecycle tests

Target size:

- 400 to 550 lines

Deliverable:

- tested base server lifecycle

### PR 5: Process Manager Reuse/Restart

Owner:

- Teammate A

Scope:

- add reuse logic
- add restart logic for model changes
- add status helpers
- add more process-manager tests

Target size:

- 250 to 450 lines

Deliverable:

- complete server lifecycle behavior

### PR 6: Inference Client

Owner:

- Teammate B

Scope:

- add `inference.py`
- connect local OpenAI-compatible client to running `llama-server`
- implement `query_text()`
- implement response cleanup and typed error handling
- add tests

Target size:

- 350 to 500 lines

Deliverable:

- local text inference through the runtime

### PR 7: Structured JSON And Grammar Support

Owner:

- Teammate B

Scope:

- extend `inference.py`
- add `query_json()`
- add grammar support for text generation
- add tests for malformed and empty output

Target size:

- 300 to 500 lines

Deliverable:

- complete inference layer for structured and plain-text responses

### PR 8: Stable Public Client

Owner:

- Teammate B

Scope:

- add `client.py`
- expose the stable public runtime API
- keep implementation thin
- add small contract tests

Target size:

- 150 to 300 lines

Deliverable:

- one import point for feature code

### PR 9: First Caller Rewire

Owner:

- Teammate B

Scope:

- rewire `src/artifactminer/RepositoryIntelligence/repo_intelligence_AI.py`
- replace direct `helpers.ollama` and `helpers.openai` calls with `artifactminer.llm.client`
- keep behavioral changes minimal
- add or update tests

Target size:

- 300 to 500 lines

Deliverable:

- first real app caller moved to the new runtime

### PR 10: Legacy Helper Cleanup

Owner:

- Teammate A and Teammate B

Scope:

- deprecate or remove `helpers/ollama.py`
- deprecate or remove direct local-provider usage in legacy code
- update imports
- update tests

Target size:

- 250 to 500 lines

Deliverable:

- fewer old entry points into local inference

## Suggested Branch Ownership

One teammate should own only the runtime process path PRs.

One teammate should own only registry and inference PRs.

Do not have both teammates editing the same new runtime file in parallel unless the work has been explicitly split.

Recommended ownership:

- Teammate A
  `errors.py`, `config.py`, `health.py`, `process_manager.py`
- Teammate B
  `models.py`, `registry.py`, `inference.py`, `client.py`

PR ownership summary:

- Teammate A owns PR 1, PR 3, PR 4, and PR 5
- Teammate B owns PR 2, PR 6, PR 7, PR 8, and PR 9
- PR 10 is shared, but Teammate A should review all lifecycle changes and Teammate B should review all caller rewires and client-surface changes

## Testing Expectations

Runtime code should be mostly unit tested with mocks.

Do not depend on real model files or a real local server for every test.

Tests should cover:

- binary missing
- model missing
- path resolution
- port allocation
- startup success
- startup timeout
- restart behavior
- server reuse behavior
- valid text response
- empty text response
- valid JSON response
- malformed JSON response

Add a small number of opt-in integration tests later if needed.

Do not block the initial runtime build on real end-to-end model tests.

## Code Review Checklist

Every runtime PR should be reviewed against this checklist:

- Is this runtime-only code, or did feature logic leak in?
- Is the public API smaller than before?
- Are errors typed and actionable?
- Is local-only behavior preserved?
- Is there any hidden cloud fallback?
- Are tests present and scoped to the same change?
- Is the PR small enough to review comfortably?

If the answer to any of these is no, split or revise the PR.

## Migration Constraints

While building the runtime:

- do not rewrite the resume pipeline yet
- do not rewrite the frontend yet
- do not move large feature modules into the runtime package
- do not mix runtime creation with major API redesign

First build the runtime.

Then rewire callers one by one.

## Definition Of Done

The runtime migration is complete when:

- `artifactminer.llm.client` is the standard app entry point for local inference
- `llama-server` is managed by one shared runtime package
- local models are resolved through one registry
- text and JSON inference are both supported through the same runtime
- feature modules no longer know about local provider implementation details
- legacy direct local-provider helper usage is removed or deprecated

## Immediate Next Step

Start with PR 1 and PR 2 only.

Do not start rewiring callers before:

- package skeleton exists
- typed errors exist
- model registry exists

That order keeps the work reviewable and prevents merge conflicts across teammates.
