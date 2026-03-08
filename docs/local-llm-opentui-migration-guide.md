# Local LLM OpenTUI Frontend Migration Guide

This document defines how to migrate the `opentui-react-exp` frontend on `origin/development` so it becomes the UI for the local-LLM workflow.

This guide assumes:

- `origin/development` is the integration target
- high rewrite is acceptable
- local-LLM workflow replaces the current demo/mock flow
- backward compatibility is not required except for preserving deterministic analysis as a capability behind the new flow

This guide is about the OpenTUI React frontend only.

## Current `origin/development` Situation

The current OpenTUI React app is still a mostly demo-oriented flow.

Relevant files:

- `opentui-react-exp/src/context/AppContext.tsx`
- `opentui-react-exp/src/index.tsx`
- `opentui-react-exp/src/api/endpoints.ts`
- `opentui-react-exp/src/components/Analysis.tsx`
- `opentui-react-exp/src/components/FileUpload.tsx`
- `opentui-react-exp/src/components/ProjectList.tsx`
- `opentui-react-exp/src/components/ResumePreview.tsx`

Main problems:

- state is still based on older analysis flow
- screen routing is not centered on local-LLM pipeline phases
- mock data still drives important UI transitions
- there is no proper draft/polish interaction loop
- API types do not yet reflect the local-LLM workflow in `development`

## Goal

Replace the current demo-style frontend flow with a local-LLM workflow-centered TUI.

The new user flow should be:

1. Landing
2. Consent / policy
3. ZIP input / context creation
4. Repo selection
5. Contributor identity selection
6. Pipeline launch / model selection
7. Live analysis + draft progress
8. Draft review / pause
9. Feedback entry for polish
10. Final resume preview

This is the target UX shape for the frontend migration.

## Target Frontend State Model

The app state should be pipeline-oriented, not old analysis-oriented.

The state should track at least:

- `zipPath`
- `intakeId`
- `detectedRepos`
- `selectedRepoIds`
- `contributors`
- `selectedEmail`
- `pipelineJobId`
- `pipelineStatus`
- `pipelineStage`
- `pipelineTelemetry`
- `pipelineMessages`
- `resumeV3Draft`
- `resumeV3Output`
- `pipelineNotice`

This is much closer to the pipeline-centric state used on the experimental line.

## Screen Ownership Model

Each screen should own UI behavior only.

The screen should not:

- know how to call subprocesses
- know runtime details
- reconstruct backend workflow rules itself

Screens should ask the API client for state and render accordingly.

## Recommended Screen Set

Recommended components:

- `Landing`
- `ConsentScreen`
- `FileUpload`
- `ProjectList`
- `IdentityScreen`
- `PipelineLaunchScreen`
- `Analysis`
- `DraftPauseScreen`
- `FeedbackScreen`
- `ResumePreview`

The current app already has some of these on the experimental side, but not on `origin/development`.

## API Client Direction

The frontend API client should move away from old analysis endpoints as the primary flow and instead use:

- `createPipelineIntake`
- `getPipelineContributors`
- `startPipeline`
- `getPipelineStatus`
- `polishPipeline`
- `cancelPipeline`

The frontend should not contain provider-specific wording like OpenAI/Ollama in its core user journey.

## State Management Rules

The app context should:

- hold pipeline workflow state
- support resetting run state without resetting the entire session
- preserve draft and final output separately

Do not keep the current older `analysisResult`, `resumeItems`, and `summaries` state model as the main flow once the migration begins.

## UI Migration Principle

This is not a skin-deep change.

The frontend should be rewritten around the local-LLM workflow rather than patched screen by screen on top of the old demo routing.

That means:

- replace old screen transitions
- replace mock-driven analysis progress
- replace old API endpoint assumptions
- replace old state shape

## Suggested Ownership

Recommended teammate:

- Frontend/OpenTUI owner

If you have two frontend people, split by:

- state/API layer owner
- screen/component owner

## PR Size Rule

Every PR should stay around 500 changed lines total.

Preferred range:

- 250 to 550 changed lines

Do not open a massive frontend rewrite PR.

## PR Sequence

### PR 1: Pipeline Types

Owner:

- Frontend/OpenTUI owner

Scope:

- add pipeline-oriented TS types
- add telemetry and output types
- avoid touching screen logic yet

Target size:

- 250 to 450 lines

### PR 2: API Endpoint Client Migration

Owner:

- Frontend/OpenTUI owner

Scope:

- add local-LLM endpoint client methods
- keep old methods temporarily if needed
- add API client tests

Target size:

- 250 to 500 lines

### PR 3: AppContext Rewrite

Owner:

- Frontend/OpenTUI owner

Scope:

- replace old app state with pipeline-centric state
- add `resetRunState`
- keep the public context clean and minimal

Target size:

- 300 to 500 lines

### PR 4: Root Navigation Rewrite

Owner:

- Frontend/OpenTUI owner

Scope:

- rewrite `src/index.tsx` screen flow
- remove mock-driven transitions
- wire in new screen order

Target size:

- 250 to 500 lines

### PR 5: Identity + Launch Screens

Owner:

- Frontend/OpenTUI owner

Scope:

- add `IdentityScreen`
- add `PipelineLaunchScreen`
- wire contributor selection and launch controls

Target size:

- 350 to 550 lines

### PR 6: Analysis Screen Migration

Owner:

- Frontend/OpenTUI owner

Scope:

- replace mock progress with real polled telemetry
- display messages and current stage
- support cancellation if desired

Target size:

- 350 to 550 lines

### PR 7: Draft Pause + Feedback Screens

Owner:

- Frontend/OpenTUI owner

Scope:

- add `DraftPauseScreen`
- add `FeedbackScreen`
- support polish submission

Target size:

- 350 to 550 lines

### PR 8: Resume Preview Migration

Owner:

- Frontend/OpenTUI owner

Scope:

- make preview work for draft and final output
- support metadata, quality info, and navigation if needed

Target size:

- 300 to 500 lines

### PR 9: Old Mock Flow Cleanup

Owner:

- Frontend/OpenTUI owner

Scope:

- remove obsolete mock data paths
- remove old unused screens or state
- simplify root flow

Target size:

- 250 to 500 lines

## Testing Expectations

Frontend tests should verify:

- endpoint client shape
- state transitions in AppContext
- screen transitions for happy path
- status polling behavior
- draft-to-polish-to-final flow
- validation for missing selection or missing feedback

Prefer small component and client tests.

Do not wait for fully integrated end-to-end tests before landing the screen architecture.

## Visual And UX Rules

The UI should make the local-LLM workflow understandable.

Users should always know:

- what stage they are in
- what the system is doing
- whether the draft is ready
- when feedback is needed
- when the final output is ready

The frontend should avoid generic “analyzing...” screens once real stage telemetry is available.

Use explicit stage labels:

- ANALYZE
- FACTS
- DRAFT
- POLISH

## Definition Of Done

The OpenTUI migration is complete when:

- the frontend no longer depends on mock analysis flow as the main product path
- the app state is pipeline-centric
- users can run the local-LLM workflow end to end from the TUI
- draft and polish phases are clearly represented in the UI
- the frontend consumes the `/local-llm` API family as the main interaction path

## Things To Avoid

- do not rewrite all screens in one PR
- do not mix large state rewrites with unrelated styling churn
- do not keep obsolete mock data around after the real flow is wired
- do not encode backend workflow policy in the frontend when the API already owns it
