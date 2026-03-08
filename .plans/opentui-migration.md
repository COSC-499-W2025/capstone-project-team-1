# OpenTUI Frontend Migration Plan

## Overview

Migrate the `opentui-react-exp` frontend from `origin/experimental-llamacpp-v3` to `origin/development`, replacing the demo-oriented flow with a local-LLM pipeline-centric TUI.

- **Source branch**: `origin/experimental-llamacpp-v3`
- **Target branch**: `origin/development`
- **Scope**: `opentui-react-exp/` only — backend migration is handled separately
- **Rule**: Port known-good code from the source branch. Do not redesign or refactor beyond what exists there.

## How to Use This Plan (for AI Agents)

1. Read this file for shared context (state model, API shape, screen flow, conventions)
2. Your issue description tells you exactly which files to create or modify
3. To see the target state of any file, run: `git show origin/experimental-llamacpp-v3:<path>`
4. Match the source branch's implementation — adapt only where `development` differs
5. Do not add features, refactoring, or changes beyond what's in the source branch

## Target User Flow

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

## Screen Enum

```typescript
export type Screen =
  | "landing"
  | "consent-policy"
  | "file-upload"
  | "project-list"
  | "identity"
  | "pipeline-launch"
  | "analysis"
  | "draft-pause"
  | "feedback"
  | "resume-preview";
```

## Target State Model (AppContext)

The app state is pipeline-oriented. Key fields:

```typescript
export interface AppState {
  zipPath: string;
  intakeId: string | null;
  detectedRepos: PipelineRepoCandidate[];
  selectedRepoIds: string[];
  contributors: PipelineContributorIdentity[];
  selectedEmail: string | null;
  pipelineJobId: string | null;
  pipelineStatus: PipelineJobStatus | "idle";
  pipelineStage: PipelineStage | null;
  pipelineTelemetry: PipelineTelemetry | null;
  pipelineMessages: string[];
  resumeV3Draft: ResumeV3Output | null;
  resumeV3Output: ResumeV3Output | null;
  pipelineNotice: string | null;
}
```

`resetRunState()` resets pipeline-run fields without wiping intake/repo selection.
`reset()` resets everything to initial state.

## API Endpoints (Local-LLM)

The frontend talks to these backend routes:

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/local-llm/context` | Create pipeline intake from ZIP |
| POST | `/local-llm/context/contributors` | Get contributors for selected repos |
| POST | `/local-llm/generation/start` | Start pipeline with model config |
| GET | `/local-llm/generation/status` | Poll pipeline status + telemetry |
| POST | `/local-llm/generation/polish` | Submit feedback for polish phase |
| POST | `/local-llm/generation/cancel` | Cancel running pipeline |

Old analysis endpoints (`/analyze`, `/resume`, `/summaries`) remain in the API client but are no longer the primary flow.

## Pipeline Types

Key types the frontend uses:

- `PipelineJobStatus`: `"queued" | "running" | "draft_ready" | "polishing" | "complete" | "error" | "cancelled" | "failed_resource_guard"`
- `PipelineStage`: `"ANALYZE" | "FACTS" | "DRAFT" | "POLISH"`
- `PipelineRepoCandidate`: `{ id, name, rel_path }`
- `PipelineContributorIdentity`: `{ email, name, repo_count, commit_count, candidate_username }`
- `PipelineTelemetry`: `{ stage, active_model, repos_total, repos_done, current_repo, ... }`
- `ResumeV3Output`: `{ professional_summary, skills_section, developer_profile, projects[], metadata, portfolio? }`

Full type definitions: see `opentui-react-exp/src/api/types.ts` on `origin/experimental-llamacpp-v3`.

## Conventions

- Framework: OpenTUI React (`@opentui/react`)
- Keyboard handling: `useKeyboard` hook from `@opentui/react`
- State: React Context via `AppProvider` / `useAppState()`
- API client: thin wrapper using `ApiClient` class in `api/client.ts`
- Styling: inline styles using the `theme` object from `types.ts`
- Tab-based indentation in all files
- Biome for linting/formatting

## Dependency Graph

```
Wave 1 (no deps):           PR1a (additive, backward-compat)

Wave 2 (after PR1a):        PR1b ◄─── (PR1a)
                            PR2  ◄─── (PR1a)
                            PR3  ◄─── (PR1a)

Wave 3 (after PR2+PR3):     PR5a ◄─── (PR2+PR3)  [Ahmad]
                            PR5b ◄─── (PR2+PR3)  [Stavan]
                            PR6a ◄─── (PR2+PR3)  [Ahmad]
                            PR7a ◄─── (PR2+PR3)  [Ahmad]
                            PR7b ◄─── (PR2+PR3)  [Stavan]
                            PR9c ◄─── (PR2+PR3)  [Stavan]

Wave 4 (after wave 3):      PR6b ◄─── (PR6a)              [Stavan]
                            PR8  ◄─── (PR1b+PR3+PR6b)     [Ahmad]
                            PR9b ◄─── (PR3)               [Ahmad]

Wave 5 (final integration): PR4  ◄─── (all screens+PR9b)  [Stavan]
                            PR9a ◄─── (PR4+PR6a)          [Stavan]
```

Key rules:
- PR1a must be additive/backward-compatible (keep legacy Screen values until PR4)
- PR6a and PR6b modify the same file — must be strictly sequential
- PR4 is the final integration PR — only merge after all screen components exist
- PR9a deletes mockProjects.ts — only after all imports are cleaned up
- PR9b renames Landing prop `onGetStarted` → `onReady` — must land before PR4

## PR Summary

| PR | Title | Owner | Wave | ~Net LOC | Key Files |
|----|-------|-------|------|----------|-----------|
| PR1a | Pipeline Types (additive) | Stavan | 1 | ~125 | `api/types.ts`, `types.ts` |
| PR1b | Resume Utils | Ahmad | 2 | ~348 | `utils/resumeText.ts`, `utils/errorMessage.ts`, `utils/index.ts`, `utils/pathHelpers.ts` |
| PR2 | API Endpoints | Stavan | 2 | ~79 | `api/endpoints.ts`, `api/client.test.ts` |
| PR3 | AppContext Rewrite | Ahmad | 2 | ~92 | `context/AppContext.tsx` |
| PR5a | IdentityScreen | Ahmad | 3 | ~252 | `components/IdentityScreen.tsx` |
| PR5b | PipelineLaunchScreen | Stavan | 3 | ~181 | `components/PipelineLaunchScreen.tsx` |
| PR6a | Analysis Polling+State | Ahmad | 3 | ~120 | `components/Analysis.tsx` (polling/state only) |
| PR7a | DraftPauseScreen | Ahmad | 3 | ~280 | `components/DraftPauseScreen.tsx` |
| PR7b | FeedbackScreen | Stavan | 3 | ~253 | `components/FeedbackScreen.tsx` |
| PR9c | FileUpload + Config | Stavan | 3 | ~103 | `FileUpload.tsx`, `searchFilter.ts`, `zipScanner.ts`, `tsconfig.json` |
| PR6b | Analysis UI Panels | Stavan | 4 | ~245 | `components/Analysis.tsx` (rendering) |
| PR8 | ResumePreview | Ahmad | 4 | ~136 | `components/ResumePreview.tsx` |
| PR9b | UI Polish & Formatting | Ahmad | 4 | ~16 | `TopBar`, `BottomBar`, `Landing`, `ConsentScreen` |
| PR4 | Root Navigation (integration) | Stavan | 5 | ~127 | `index.tsx` |
| PR9a | Mock Cleanup + ProjectList | Stavan | 5 | ~130 | `data/mockProjects.ts` (delete), `components/ProjectList.tsx` |

## Backend Dependency Note

The backend `/local-llm/*` routes are being migrated separately by the backend team. The frontend PRs can be coded, reviewed, and merged independently — the API client methods are just HTTP wrappers. End-to-end testing requires the backend routes to be live.
