# Local LLM API Migration Plan

## Purpose

This document explains the API migration we want on `origin/development` so the backend exposes the local LLM workflow as a first-class product path.

This file is meant for team review. It describes the intent, boundaries, target API surface, and implementation sequencing for the API layer only.

## Why This Plan Exists

Right now the project has two different states:

- `origin/development` has the current main API surface, including `consent`, `zip`, `analyze`, `projects`, `resume`, `portfolio`, and `openai`
- `origin/experimental-llamacpp-v3` already proves a working `/local-llm/*` HTTP flow, but its implementation is still prototype-shaped and not organized the way we want long term on `development`

The goal of this migration is not to copy the experimental branch blindly.

The goal is to bring the local-LLM API surface into `development` in a way that:

- preserves the correct `development` contracts that should stay
- reuses the proven endpoint behavior from the experimental branch
- keeps API ownership separate from runtime and service-layer ownership
- gives the frontend and other clients a stable route family to build against

## Current Situation

### On `origin/development`

Confirmed API facts:

- the consent API already exists
- the consent literals already support `none | local | local-llm | cloud`
- there is no `/local-llm/*` route family yet
- `POST /openai` is still part of the public API surface
- `/resume/*` is still part of the public API surface and reflects the older resume/evidence path

### On `origin/experimental-llamacpp-v3`

Confirmed API facts:

- the full local-LLM route family already exists
- the route family is:
  - `POST /local-llm/context`
  - `POST /local-llm/context/contributors`
  - `POST /local-llm/generation/start`
  - `GET /local-llm/generation/status`
  - `POST /local-llm/generation/polish`
  - `POST /local-llm/generation/cancel`
- those routes currently live inside `src/artifactminer/api/resume.py`
- that branch still uses an older consent vocabulary, so its consent schema should not be copied over `development`

## What We Are Trying To Do

We want `origin/development` to expose a clear local-LLM API family that represents the actual workflow clients will use:

1. create context from a ZIP
2. choose repositories
3. discover contributors
4. start generation
5. poll generation status
6. polish a draft
7. cancel generation if needed

In other words, we want the HTTP surface to reflect the workflow directly instead of forcing clients to stitch together older routes or provider-specific endpoints.

## Migration Goals

- add a dedicated `/local-llm/*` route family to `origin/development`
- keep the existing `development` consent API contract unchanged
- introduce local-LLM transport schemas that are workflow-oriented
- mount the new route family explicitly in `app.py`
- make `/resume/*` clearly transitional where relevant to API-facing documentation
- remove `/openai` from the public API surface after the new route family is in place
- keep the API layer small, explicit, and testable

## Non-Goals

This plan is not responsible for:

- `llama-server` process management
- model registry/runtime abstraction
- moving orchestration into a new service package
- job-store redesign
- extractor or prompt redesign
- frontend migration details
- consent-model redesign on `development`

Those concerns belong to other migration plans.

## Design Decisions

 **1. Keep the `development` consent API as-is**

We already have a usable consent contract on `development`:

- `GET /consent`
- `PUT /consent`

and the allowed literals are already appropriate for local-vs-cloud behavior:

- `none`
- `local`
- `local-llm`
- `cloud`

That means this migration should not touch consent shape or vocabulary unless a real incompatibility is discovered later.

**2. Add a dedicated local-LLM router**

The local workflow should live under its own route family:

- `/local-llm`

Recommended files:

```text
src/artifactminer/api/local_llm.py
src/artifactminer/api/local_llm_schemas.py
```

This keeps the route family readable and prevents `resume.py` from becoming the long-term home for unrelated workflow state.

**3. Keep `/resume/*` for now, but treat it as transitional**

The existing `/resume/*` routes should remain during this migration, but they should no longer be treated as the main product path for local generation.

That means:

- do not remove `/resume/*` in this migration
- do not expand `/resume/*` to absorb the new workflow
- describe it as transitional where API-facing docs discuss the route surface

**4. Remove `/openai` after the new route family lands**

`POST /openai` is provider-specific and does not fit the desired product API.

It can remain temporarily while the new route family is introduced, but once `/local-llm/*` is present and verified, `/openai` should be removed from the public API surface.

## Target API Surface

The target route family for this migration is:

- `POST /local-llm/context`
- `POST /local-llm/context/contributors`
- `POST /local-llm/generation/start`
- `GET /local-llm/generation/status`
- `POST /local-llm/generation/polish`
- `POST /local-llm/generation/cancel`

These routes should use workflow-oriented request and response models rather than provider-oriented naming.

## Route Layer Responsibilities

The route layer should:

- validate request payloads
- bind those payloads to local-LLM transport schemas
- call the underlying application/service functionality
- map failures to stable HTTP status codes
- return typed response payloads

The route layer should not:

- manage subprocesses directly
- own model lifecycle
- hold orchestration state long term
- embed runtime-specific logic

## Error Contract

The API surface should converge on these route-level semantics:

- `404` when no active context or active job exists
- `409` for invalid workflow state transitions
- `422` for invalid or missing client input
- `500` for unexpected failures surfaced at the API boundary

Examples:

- requesting contributors before context exists -> `404`
- requesting polish before a draft exists -> `409`
- invalid email or empty feedback payload -> `422`
- unexpected runtime or route failure -> `500`

## Testing Expectations

Each API change should include its own route-level tests rather than deferring all verification to the end.

That means each route should add or update tests for:

- request validation
- expected success responses
- expected error responses
- route registration where relevant

This keeps each PR reviewable and makes the migration safer to merge incrementally.

## Recommended Sequencing

The implementation should move in this order:

1. define the local-LLM transport schemas
2. introduce the new router and register it in `app.py`
3. add the context and contributor routes
4. add the generation routes
5. normalize route-level error behavior across the route family
6. update API-facing docs to show the new route family and mark `/resume/*` transitional
7. remove `/openai` from the public API surface

This sequencing is important because it lets the team stabilize the contract before cleanup work starts.

## Scope Boundaries For Teammates

This plan is specifically for the backend/API owner (Shlok)

The API owner should own:

- schema modules
- route modules
- app registration
- route-level tests
- API-surface documentation cleanup

The API owner should coordinate with, but not absorb the work of:

- the runtime owner
- the service-layer owner
- the frontend/OpenTUI owner

## Source References

Primary implementation reference:

- `origin/experimental-llamacpp-v3:src/artifactminer/api/resume.py`
- `origin/experimental-llamacpp-v3:src/artifactminer/api/app.py`
- `origin/experimental-llamacpp-v3:src/artifactminer/api/schemas.py`

Target branch reference:

- `origin/development:src/artifactminer/api/app.py`
- `origin/development:src/artifactminer/api/schemas.py`
- `origin/development:src/artifactminer/api/resume.py`
- `origin/development:src/artifactminer/api/openai.py`

Planning reference:

- `docs/local-llm-api-migration-guide.md`
