# Local LLM API Migration Guide

This document defines how to migrate the API layer on `origin/development` so the app exposes the local-LLM workflow as the main backend path.

This guide assumes:

- `origin/development` is the integration target
- high rewrite is acceptable
- backward compatibility is not required except keeping deterministic analysis available
- old provider-specific endpoints may be removed or replaced

This guide is about the HTTP/API layer only.

## Goal

Create a clean API surface for the local-LLM product flow.

The API layer should:

- expose the local generation workflow clearly
- use transport-specific schemas only
- call the service layer instead of embedding orchestration
- stop exposing provider-specific cloud routes as first-class product paths

## Current `origin/development` Situation

Current `origin/development` includes:

- `src/artifactminer/api/app.py`
- `src/artifactminer/api/openai.py`
- `src/artifactminer/api/resume.py`
- `src/artifactminer/api/analyze.py`
- `src/artifactminer/api/schemas.py`

Issues:

- `/openai` is provider-specific and cloud-branded
- current `/resume` routes are tied to older resume/evidence generation
- route files own too much policy
- there is no stable local-LLM route family in `development`

## Product API Direction

The local-LLM flow should become its own route family.

Recommended router:

- `/local-llm`

Recommended endpoint families:

- `/local-llm/context`
- `/local-llm/context/contributors`
- `/local-llm/generation/start`
- `/local-llm/generation/status`
- `/local-llm/generation/polish`
- `/local-llm/generation/cancel`

This is the same architectural direction already proven on the experimental branch.

## Target Files

Recommended target files:

```text
src/artifactminer/api/local_llm.py
src/artifactminer/api/local_llm_schemas.py
```

Optional alternative:

- keep schemas in `schemas.py`

Preferred approach:

- create a separate local schema module to keep the transport contract readable

## What To Keep

Keep and preserve:

- existing deterministic analysis endpoints if they still serve non-LLM paths
- general project, evidence, and retrieval endpoints unless they conflict directly
- database-backed project data that still feeds the local-LLM flow

## What To Replace

Plan to replace or de-emphasize:

- `src/artifactminer/api/openai.py`
- direct provider-specific LLM route naming
- transport-level logic that knows about old local/cloud provider choice

If the team keeps `/openai` temporarily, it should be transitional only.

It should not remain the main product route if local LLM is the primary path.

## Route Layer Responsibilities

The route layer should only do these things:

- validate requests
- call service-layer methods
- map service/runtime errors to HTTP status codes
- return response payloads

The route layer should not:

- manage subprocesses
- manage active jobs directly
- hold orchestration state directly
- implement pipeline logic

## Schema Design Rules

Transport schemas should be local-LLM workflow oriented, not provider oriented.

Recommended schema families:

- intake request/response
- repo candidate response
- contributor identity response
- pipeline start request/response
- pipeline status response
- polish request/response
- cancel response
- telemetry response
- resume draft/output response

Do not name schemas after OpenAI or Ollama.

Name them after workflow state.

## Error Mapping Guidance

Recommended HTTP behavior:

- `404` when there is no active context or job
- `409` for invalid pipeline state transitions
- `422` for invalid or missing input
- `500` for unexpected service/runtime failures

Examples:

- no active context -> `404`
- polish requested before draft exists -> `409`
- invalid email or empty feedback -> `422`
- runtime crash or unexpected exception -> `500`

## App Registration Changes

`src/artifactminer/api/app.py` should eventually:

- include the new local-LLM router
- stop making provider-specific LLM routes the primary entry point

The desired shape is:

- app startup and router mounting stay clean
- local-LLM routes are mounted explicitly
- old route families are removed or left transitional only

## Suggested Ownership

Recommended teammate:

- Backend/API owner

This person should coordinate closely with the service-layer owner.

If those are different people:

- API owner owns route and schema files
- service owner owns orchestration files

## PR Size Rule

Every PR should stay around 500 changed lines total.

Preferred range:

- 250 to 550 changed lines

## PR Sequence

### PR 1: Local LLM Schema Module

Owner:

- Backend/API owner

Scope:

- add `local_llm_schemas.py`
- define transport models for intake, contributors, generation, status, polish, cancel
- add schema tests if appropriate

Target size:

- 300 to 500 lines

### PR 2: Local LLM Router Skeleton

Owner:

- Backend/API owner

Scope:

- add `local_llm.py`
- wire empty or stubbed route handlers to the service layer interface
- mount the router in `app.py`

Target size:

- 250 to 450 lines

### PR 3: Intake + Contributor Routes

Owner:

- Backend/API owner

Scope:

- implement `/context`
- implement `/context/contributors`
- map service errors to HTTP
- add route tests

Target size:

- 350 to 550 lines

### PR 4: Generation Start + Status Routes

Owner:

- Backend/API owner

Scope:

- implement `/generation/start`
- implement `/generation/status`
- add route tests

Target size:

- 350 to 550 lines

### PR 5: Polish + Cancel Routes

Owner:

- Backend/API owner

Scope:

- implement `/generation/polish`
- implement `/generation/cancel`
- add route tests

Target size:

- 300 to 500 lines

### PR 6: Remove Or Deprecate Provider-Specific API Paths

Owner:

- Backend/API owner

Scope:

- deprecate or remove `/openai`
- clean route registration
- update tests and any API docs

Target size:

- 250 to 500 lines

## Testing Expectations

API tests should verify:

- context creation success and failure
- contributor discovery from selected repos only
- generation start request validation
- status behavior with and without active jobs
- polish request validation and invalid-state behavior
- cancel behavior
- error code mapping for service/runtime failures

Prefer mocked service tests at the route layer.

Do not require real local model startup for every API test.

## Definition Of Done

The API migration is complete when:

- `development` exposes a stable `/local-llm` route family
- route handlers call the service layer instead of embedding orchestration
- provider-specific `/openai`-style routes are removed or no longer the main path
- route contracts match the local-LLM product flow

## Things To Avoid

- do not combine router creation with service implementation in one giant PR
- do not let route modules own in-memory orchestration state long-term
- do not expose local provider details in route names or schema names
