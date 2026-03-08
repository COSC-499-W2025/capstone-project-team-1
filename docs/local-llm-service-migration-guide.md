# Local LLM Service Layer Migration Guide

This document defines how to migrate the backend service/orchestration layer into `origin/development` for the local-LLM architecture.

This guide assumes:

- `origin/development` is the integration target
- local LLM is the main product path
- backward compatibility is not a goal except for preserving deterministic analysis and skill extraction
- old provider-specific paths should be replaced, not preserved long-term

This guide is about the service layer only.

It is not the runtime guide.

The runtime guide lives in:

- [local-llm-runtime-migration-guide.md](/Users/Shlok/Seventh%20Term/Capstone/capstone-project-team-1/docs/local-llm-runtime-migration-guide.md)

## Goal

Create an application-facing local-LLM service layer that sits above the runtime and below the API routes.

This layer should own:

- intake lifecycle
- repository selection flow
- contributor discovery for selected repos
- generation job lifecycle
- cancellation
- progress telemetry
- phase transitions
- draft preservation between phases
- final output packaging

This layer should not own:

- `llama-server` process management
- raw inference calls
- frontend state
- HTTP route definitions
- feature prompts

## Why This Layer Is Needed

Right now the experimental local-LLM flow puts too much orchestration inside the route module itself.

On the experimental line, job and intake state are tied directly to the FastAPI route module.

That is good enough for a working prototype, but it is not the right long-term shape for `development`.

The problem with leaving orchestration inside route files is:

- API files become too large
- route transport and domain orchestration are mixed together
- testing job behavior requires route-heavy tests
- replacement of route contracts becomes expensive
- concurrency and cancellation logic become hard to reason about

The service layer fixes this by moving workflow ownership into one application module.

## Current `origin/development` Situation

`origin/development` still uses older feature-oriented backend flows.

Relevant files include:

- `src/artifactminer/api/app.py`
- `src/artifactminer/api/analyze.py`
- `src/artifactminer/api/resume.py`
- `src/artifactminer/api/openai.py`
- `src/artifactminer/RepositoryIntelligence/repo_intelligence_AI.py`

What is missing:

- no dedicated local-LLM orchestration module
- no unified intake/job abstraction
- no stable service interface for the local pipeline

## Target Location

Create a new package:

```text
src/artifactminer/llm/service/
```

Recommended layout:

```text
src/artifactminer/llm/service/
  __init__.py
  models.py
  errors.py
  intake_service.py
  contributor_service.py
  generation_service.py
  job_store.py
  telemetry.py
```

Do not put this under:

- `src/artifactminer/api/`
- `src/artifactminer/resume/`

Why:

- this is application orchestration, not HTTP transport
- it should be callable from multiple transports later if needed

## Responsibilities By File

### `models.py`

Own service-layer data structures.

Examples:

- `IntakeState`
- `RepoCandidate`
- `GenerationJob`
- `PipelineTelemetryState`
- `FeedbackPayload`

These should be transport-neutral.

### `errors.py`

Own typed service-layer exceptions.

Examples:

- `LocalLLMServiceError`
- `ActiveContextNotFoundError`
- `GenerationJobNotFoundError`
- `InvalidPipelineStateError`
- `ContributorDiscoveryError`
- `IntakeCreationError`

### `job_store.py`

Own storage for intakes and jobs.

Start with an in-memory implementation.

Do not hard-wire global dictionaries into route files.

This module should expose interfaces like:

- `create_intake()`
- `get_active_intake()`
- `set_active_intake()`
- `create_job()`
- `get_job()`
- `set_active_job()`
- `clear_active_job()`
- `update_job()`

### `intake_service.py`

Own:

- ZIP validation
- extraction workspace creation
- repo discovery
- repo candidate normalization
- active-context replacement behavior

This service should not know about HTTP.

### `contributor_service.py`

Own contributor discovery from selected repos.

This service should:

- accept repo paths or repo candidates
- inspect git history
- aggregate contributor identities
- return stable contributor objects sorted by signal

### `telemetry.py`

Own telemetry defaults and update helpers.

This service should:

- initialize telemetry state
- update stage and progress counters
- update current repo
- serialize telemetry into transport-ready shape

### `generation_service.py`

This is the main orchestration module.

It should own:

- start generation
- run phase 1
- save draft
- run polish
- cancel generation
- cleanup job resources
- resource-guard integration
- final output handoff

This service should call:

- runtime client
- pipeline/extractor code
- job store
- telemetry helpers

This service should not:

- define FastAPI response models
- parse request bodies

## Service Boundary

The API layer should eventually call the service layer through a narrow interface like:

- `create_intake(zip_path: str) -> IntakeState`
- `list_contributors(intake_id: str, repo_ids: list[str]) -> list[Contributor]`
- `start_generation(...) -> GenerationJob`
- `get_generation_status(job_id: str) -> GenerationJob`
- `polish_generation(job_id: str, feedback: FeedbackPayload) -> GenerationJob`
- `cancel_generation(job_id: str) -> None`

The route layer should only:

- validate request payloads
- map exceptions to HTTP status codes
- return response models

## Deterministic Analysis Preservation

The one compatibility requirement we are preserving is deterministic analysis.

This means the service-layer migration must continue to use and preserve:

- skill extraction
- repo stats
- git-based deterministic analysis
- evidence-oriented deterministic signals

The service layer may replace old orchestration, but it should not throw away deterministic analysis that feeds the local-LLM path.

## Integration Rules

Allowed dependencies:

- `llm.service.*` can call `llm.client`
- `llm.service.*` can call deterministic analysis modules
- `llm.service.*` can call resume pipeline modules if needed

Disallowed dependencies:

- `llm.service.*` importing route modules
- `llm.service.*` importing frontend modules
- `llm.service.*` importing provider-specific helpers directly

## Suggested Ownership

Recommended teammate:

- Backend/Service owner

This person should be separate from the runtime owner if possible.

If the team is small, this role can be paired with the API owner, but the service code should still stay in its own package.

## PR Size Rule

Every PR should stay around 500 changed lines total.

Preferred range:

- 250 to 550 changed lines

If a change is larger, split it.

## PR Sequence

### PR 1: Service Package Skeleton

Owner:

- Backend/Service owner

Scope:

- create `src/artifactminer/llm/service/`
- add `__init__.py`
- add `models.py`
- add `errors.py`
- add empty `job_store.py`
- add empty `telemetry.py`

Target size:

- 250 to 400 lines

### PR 2: Job Store

Owner:

- Backend/Service owner

Scope:

- implement in-memory intake and job storage
- remove need for route-level global dicts in new code
- add unit tests

Target size:

- 300 to 500 lines

### PR 3: Intake Service

Owner:

- Backend/Service owner

Scope:

- implement ZIP validation hooks
- implement repo discovery orchestration
- implement active intake replacement behavior
- add tests

Target size:

- 300 to 500 lines

### PR 4: Contributor Service

Owner:

- Backend/Service owner

Scope:

- implement contributor aggregation from selected repos
- add sorting and normalization
- add tests

Target size:

- 250 to 450 lines

### PR 5: Telemetry Helpers

Owner:

- Backend/Service owner

Scope:

- implement telemetry default state
- implement stage/progress update helpers
- add tests

Target size:

- 200 to 350 lines

### PR 6: Generation Service Phase 1

Owner:

- Backend/Service owner

Scope:

- implement start-generation path
- integrate runtime client
- integrate pipeline phase 1
- save draft output into job state
- add tests with mocks

Target size:

- 400 to 550 lines

### PR 7: Generation Service Polish + Cancel

Owner:

- Backend/Service owner

Scope:

- implement polish path
- implement cancel path
- implement cleanup behavior
- add tests

Target size:

- 350 to 550 lines

### PR 8: Resource Guard + Error Mapping

Owner:

- Backend/Service owner

Scope:

- add resource-guard behavior
- add service-level error normalization
- add tests

Target size:

- 250 to 450 lines

## Definition Of Done

The service-layer migration is complete when:

- route modules no longer own job orchestration
- service code owns intake and generation lifecycle
- cancellation and telemetry are no longer route-specific hacks
- runtime calls happen only through `artifactminer.llm.client`
- deterministic analysis remains available as input to the local-LLM flow

## Things To Avoid

- do not move HTTP response models into the service layer
- do not keep orchestration globals inside route modules once service modules exist
- do not make the service layer depend directly on `llama-server` subprocess code
- do not bundle service migration with large frontend changes in the same PR
