# PI Agent PR Split Plan

Last updated: 2026-03-23

## Purpose

This document captures the current state of the `experimental/pi-agent` work and a recommended plan to split it into smaller pull requests that target `development`.

The goal is to preserve enough context that a future chat session can continue the work without re-discovering:

- what branch we started from
- what files are involved
- why a single PR is too large
- how to split the work into reviewable units
- what order to extract the PRs in
- what tradeoffs and risks to watch for

## Repository Context

- Current working directory during planning: `opentui-react-exp`
- Git repository root is one level higher: `/Users/Shlok/Seventh Term/Capstone/capstone-project-team-1`
- Current feature branch at planning time: `experimental/pi-agent`
- Intended PR target branch: `development`
- Baseline branch used for comparison in this plan: `origin/development`

Important context: this project lives inside a larger git repository. Some `git diff` outputs may show paths prefixed with `opentui-react-exp/` because the repo root is the parent directory, not this folder.

## Why We Are Splitting This Work

The current `experimental/pi-agent` branch is too large to open as one PR against `development`.

At planning time, the compare against `origin/development` is approximately:

- 27 changed files
- about 3455 insertions
- about 61 deletions

That is too large for the capstone PR size guideline of roughly 1000 LOC per PR.

We discussed two structural options:

- stacked PRs
- multiple independent PRs

GitHub does support a manual stacked workflow by opening a PR against another branch and later changing the base branch. However, for this capstone context, the preferred approach is to avoid stacking unless strictly necessary and instead create several smaller PRs directly off `development`.

## Recommendation Summary

Recommended strategy: split the current branch into 4 smaller PRs, all ultimately targeting `development`.

Preferred shape:

1. Backend and agent foundation
2. TUI authentication and model selection
3. TUI generation and progress experience
4. TUI preview and profile presentation

This keeps each PR closer to the review limit and makes the intent of each PR easier to explain.

## Current Changed Files Against `origin/development`

These were the files in the current compare at planning time:

- `.gitignore`
- `bun.lock`
- `package.json`
- `src/agent/index.ts`
- `src/agent/prompt.ts`
- `src/agent/session.ts`
- `src/api/endpoints.ts`
- `src/api/types.ts`
- `src/components/CloudResumePreview.tsx`
- `src/components/ConsentScreen.tsx`
- `src/components/FileUpload.tsx`
- `src/components/cloud-ai/CloudAuth.tsx`
- `src/components/cloud-ai/CloudFlow.tsx`
- `src/components/cloud-ai/CopilotLogin.tsx`
- `src/components/cloud-ai/ModelList.tsx`
- `src/components/cloud-ai/ModelPicker.tsx`
- `src/components/cloud-ai/SnakeGame.tsx`
- `src/components/cloud-ai/SnakeWithProgress.tsx`
- `src/components/cloud-ai/humanize.ts`
- `src/components/cloud-ai/index.ts`
- `src/components/cloud-ai/shared.ts`
- `src/dev-screen.tsx`
- `src/hooks/useSelectionCopy.ts`
- `src/index.tsx`
- `src/types.ts`
- `../src/artifactminer/api/schemas.py`
- `../src/artifactminer/api/zip.py`

Note: the last two files are outside `opentui-react-exp` but are still part of the same git repository and belong to the backend-related changes.

## Proposed Branch and PR Structure

These names are suggestions, not requirements.

### PR 1: Backend and Agent Foundation

Proposed branch name:

- `pi-agent-backend-foundation`

Target:

- `development`

Primary purpose:

- introduce or refine the agent-side session and prompt foundation
- add API and schema support needed for the PI agent workflow
- keep this PR mostly backend and shared contract focused

Expected files:

- `src/agent/index.ts`
- `src/agent/prompt.ts`
- `src/agent/session.ts`
- `src/api/endpoints.ts`
- `src/api/types.ts`
- `../src/artifactminer/api/schemas.py`
- `../src/artifactminer/api/zip.py`

Files to include only if truly required for backend compilation or contracts:

- `package.json`
- `bun.lock`
- `.gitignore`
- `src/types.ts`

Review framing:

- this PR should explain the PI agent execution model
- this PR should explain any new API contract or schema additions
- this PR should avoid bringing in UI-heavy changes

Potential risk:

- `src/api/types.ts` may also be needed by UI PRs; if that file grows too much, we may need to split only the shared type additions required for backend into this PR and defer UI-only shape changes to a later PR

### PR 2: TUI Authentication and Model Selection

Proposed branch name:

- `pi-agent-tui-auth`

Target:

- `development`

Primary purpose:

- add the cloud-auth and sign-in flow
- add model selection and related state wiring
- keep this PR focused on entering the cloud AI path, not on generation visuals or preview polish

Expected files:

- `src/components/ConsentScreen.tsx`
- `src/components/cloud-ai/CloudAuth.tsx`
- `src/components/cloud-ai/CopilotLogin.tsx`
- `src/components/cloud-ai/ModelList.tsx`
- `src/components/cloud-ai/ModelPicker.tsx`
- `src/components/cloud-ai/index.ts`
- `src/index.tsx`
- `src/types.ts`
- `src/dev-screen.tsx`

Possible shared dependencies:

- `package.json`
- `bun.lock`

Review framing:

- entering the PI agent flow
- authenticating the user
- choosing the cloud model
- minimal navigation and state wiring necessary to reach the next screen

Potential risk:

- `src/index.tsx` is touched by almost every TUI slice, so extraction order and cherry-picks need to be done carefully

### PR 3: TUI Generation and Progress Experience

Proposed branch name:

- `pi-agent-tui-generation`

Target:

- `development`

Primary purpose:

- implement the actual in-progress experience while generation runs
- isolate the gameplay, progress, and flow orchestration

Expected files:

- `src/components/cloud-ai/CloudFlow.tsx`
- `src/components/cloud-ai/SnakeGame.tsx`
- `src/components/cloud-ai/SnakeWithProgress.tsx`
- `src/components/cloud-ai/shared.ts`
- `src/components/cloud-ai/humanize.ts`
- `src/components/cloud-ai/index.ts`
- `src/index.tsx`
- `src/dev-screen.tsx`
- `src/hooks/useSelectionCopy.ts`
- `src/components/FileUpload.tsx`

Review framing:

- generation screen behavior
- progress UI
- interactive polish during long-running work
- any developer harness changes used to exercise the generation flow

Potential risk:

- this PR likely depends on some auth or model selection state shape from PR 2
- if independent extraction becomes painful, this PR is the best candidate for a stacked PR, but only if necessary

### PR 4: TUI Preview and Profile Presentation

Proposed branch name:

- `pi-agent-tui-preview`

Target:

- `development`

Primary purpose:

- add the resume preview and developer profile presentation
- focus on the output and browsing experience after generation succeeds

Expected files:

- `src/components/CloudResumePreview.tsx`
- `src/api/types.ts`
- `src/agent/prompt.ts`
- `src/agent/session.ts`
- `src/index.tsx`
- `src/components/cloud-ai/CloudFlow.tsx`
- `src/components/cloud-ai/SnakeWithProgress.tsx`

Important note:

This PR is the least independent of the four. It introduces or uses structured profile data such as `DeveloperProfile`, `GrowthArea`, and related preview tabs. Some of that logic currently spans backend and frontend files.

Because of that, there are two acceptable ways to handle PR 4:

- preferred: keep only the minimum shared type and agent changes needed for the preview contract and place the rest in this PR
- fallback: move the `DeveloperProfile` contract and generation shape into PR 1 if that leads to a much cleaner split

Review framing:

- resume preview experience
- structured developer profile output
- insights, projects, growth areas, and tab navigation

## Extraction Strategy From `experimental/pi-agent`

The current branch already mixes all four areas together. This means we should not branch blindly from the current head and open PRs. Instead, we should extract each PR deliberately.

Recommended extraction workflow:

1. Start from a clean local `development` branch.
2. Create a new branch for PR 1 from `development`.
3. Cherry-pick only the commits or file hunks needed for PR 1.
4. Run tests or targeted verification for PR 1.
5. Open PR 1 to `development`.
6. Repeat the process for PR 2 from `development`.
7. Repeat for PR 3 from `development`.
8. Repeat for PR 4 from `development`.

Important: do not assume commit boundaries map perfectly onto PR boundaries. Several commits in `experimental/pi-agent` touch shared files like `src/index.tsx`, `src/api/types.ts`, `src/agent/prompt.ts`, and `src/agent/session.ts`. That means we may need a mix of:

- cherry-picking whole commits
- cherry-picking with conflict resolution
- manually applying only parts of a commit

## Practical Extraction Principles

When splitting this branch, follow these rules:

- prefer self-contained PRs over perfect historical commit preservation
- keep each PR small enough to review comfortably
- if a shared file is touched by many slices, include only the minimum needed for that PR
- if one feature depends heavily on another, either move the shared contract earlier or use a temporary stacked PR only for that pair
- avoid rewriting unrelated code just to make the split look cleaner

## Commits Observed in the Current Branch

The branch history shows several broad themes:

- backend and process management work
- initial cloud generation TUI
- later refactor from `CloudGeneration` to `CloudFlow`
- auth and model selection additions
- snake/progress experience
- developer profile and richer preview output
- cleanup commits removing obsolete components and unused exports

This means future sessions should expect the split to be based more on feature slices than on a simple commit range.

## Likely Pain Points

These are the files most likely to need careful manual splitting:

- `src/index.tsx`
- `src/api/types.ts`
- `src/agent/prompt.ts`
- `src/agent/session.ts`
- `src/components/cloud-ai/index.ts`
- `src/dev-screen.tsx`

Reason: these files act as glue and were updated multiple times as the feature evolved.

## Decision Rules for Shared Files

If a future session is unsure where a shared change belongs, use these rules:

- If the change defines the data shape returned by the agent, it probably belongs in PR 1.
- If the change exists only to render or navigate UI, it probably belongs in a TUI PR.
- If the change is required only for preview tabs, developer profile display, or growth areas, it probably belongs in PR 4.
- If the change exists only for sign-in, model selection, or cloud entry flow, it probably belongs in PR 2.
- If the change exists only for long-running progress or gameplay during generation, it probably belongs in PR 3.

## Preferred Order of Work

Recommended order:

1. Extract PR 1 first.
2. Extract PR 2 second.
3. Extract PR 3 third.
4. Extract PR 4 last.

Why this order:

- backend contracts should settle first
- auth and model selection are easier to reason about before generation polish
- preview UI is the most contract-sensitive and should come after earlier decisions are stable

## When Stacking Becomes Acceptable

The preferred plan is non-stacked PRs to `development`.

However, if PR 3 or PR 4 cannot be made reviewable without code that only exists in another unmerged PR, then stacking is acceptable as a fallback.

Example fallback:

- PR 1: `pi-agent-backend-foundation` -> `development`
- PR 2: `pi-agent-tui-auth` -> `development`
- PR 3: `pi-agent-tui-generation` -> `pi-agent-tui-auth`

If that happens, note it clearly in the PR description and retarget the later PR once its base merges.

## Suggested Command-Level Workflow

These are example commands only. A future session should verify branch names and local status first.

Create PR 1 branch from development:

```bash
git checkout development
git pull
git checkout -b pi-agent-backend-foundation
```

Create PR 2 branch from development:

```bash
git checkout development
git pull
git checkout -b pi-agent-tui-auth
```

Create PR 3 branch from development:

```bash
git checkout development
git pull
git checkout -b pi-agent-tui-generation
```

Create PR 4 branch from development:

```bash
git checkout development
git pull
git checkout -b pi-agent-tui-preview
```

Note: because the active repository root is the parent directory, commands should be run from the git root or with care from the `opentui-react-exp` directory.

## What A Future Session Should Do First

If a later chat session resumes this work, the first steps should be:

1. Confirm the current branch and working tree state.
2. Re-run `git diff --stat origin/development...HEAD`.
3. Check whether any of the proposed split branches already exist.
4. Decide whether to extract PR 1 by commit cherry-pick, file checkout, or manual patching.
5. Start with PR 1 and do not attempt all four extractions at once.

## Success Criteria

This plan is successful if:

- no single PR is close to the original 3.5k LOC size
- each PR has a clear story for reviewers
- shared files are split with minimal confusion
- the work remains targetable to `development`
- a future session can continue from this document alone

## Current Recommendation

Do not open `experimental/pi-agent` directly against `development`.

Instead:

- treat `experimental/pi-agent` as the source branch to mine changes from
- extract 4 smaller PR branches off `development`
- only use stacking if one of the later TUI slices truly cannot stand on its own

## Document Maintenance

If the split plan changes, update this file rather than relying on chat history.

In particular, future sessions should add:

- actual branch names created
- which commits were cherry-picked into each branch
- which conflicts were resolved manually
- final PR numbers once opened
