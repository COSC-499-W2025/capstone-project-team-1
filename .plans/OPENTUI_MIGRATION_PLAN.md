# OpenTUI Migration Plan - Artifact Miner TUI

**Date:** January 2026  
**Branch:** `296-opentui-experiment`  
**Goal:** Migrate from Textual TUI to OpenTUI React with full API integration

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Current State Analysis](#current-state-analysis)
3. [Architecture Design](#architecture-design)
4. [Implementation Phases](#implementation-phases)
5. [API Integration Strategy](#api-integration-strategy)
6. [Component Specifications](#component-specifications)
7. [State Management](#state-management)
8. [UI/UX Improvements](#uiux-improvements)
9. [Testing Strategy](#testing-strategy)
10. [Migration Checklist](#migration-checklist)

---

## Executive Summary

### What We Have
- **Textual TUI** (`src/artifactminer/tui/`): Fully functional Python-based TUI with 8 screens
- **OpenTUI Mock** (`opentui-react-exp/`): React-based visual prototype with 6 screens using mock data
- **Backend API**: FastAPI server with all endpoints needed

### What We Need
1. Create TypeScript API client for OpenTUI
2. Add missing UserConfig screen to OpenTUI
3. Connect all screens to real API endpoints
4. Implement proper state management for cross-screen data flow
5. Enhance UI with better animations and feedback

### Effort Estimate
- **Phase 1 (Foundation):** 2-3 days
- **Phase 2 (Core Screens):** 3-4 days
- **Phase 3 (Polish & Testing):** 2-3 days
- **Total:** ~8-10 days

---

## Current State Analysis

### Textual TUI Screens (Python)

| Screen | File | API Calls | State Managed |
|--------|------|-----------|---------------|
| WelcomeScreen | `welcome.py` | None | None |
| ConsentScreen | `consent.py` | `PUT /consent` | `consent_level` |
| UserConfigScreen | `userconfig.py` | `GET /questions`, `POST /answers` | `user_email`, answers |
| UploadScreen | `upload.py` | `POST /zip/upload`, `GET /zip/{id}/directories` | `zip_id`, file path |
| FileBrowserScreen | `file_browser.py` | None (local filesystem) | selected path |
| ListContentsScreen | `list_contents.py` | None (data passed in) | selected directories |
| AnalyzingScreen | `analyzing.py` | Implicit (analysis triggered) | `zip_id` |
| ResumeScreen | `resume.py` | `GET /resume`, `GET /summaries` | resume items, summaries |

### OpenTUI Mock Screens (TypeScript/React)

| Screen | File | Current State | Needs |
|--------|------|---------------|-------|
| Landing | `Landing.tsx` | ✅ Complete with animations | Minor tweaks |
| ConsentScreen | `ConsentScreen.tsx` | Mock selection only | API integration |
| FileUpload | `FileUpload.tsx` | Hardcoded file browser | Real file picker + API |
| ProjectList | `ProjectList.tsx` | Uses `mockProjects` | API integration |
| Analysis | `Analysis.tsx` | Simulated progress | Real analysis API |
| ResumePreview | `ResumePreview.tsx` | Uses `mockResumeData` | API integration |
| **UserConfig** | **MISSING** | N/A | Create from scratch |

### Backend API Endpoints

```
GET  /health                    # Health check
GET  /consent                   # Get current consent
PUT  /consent                   # Update consent level
GET  /questions                 # Get user config questions
POST /answers                   # Submit answers
POST /zip/upload                # Upload ZIP file
GET  /zip/{zip_id}/directories  # List ZIP contents
POST /analyze/{zip_id}          # Run analysis
GET  /summaries                 # Get project summaries (by email)
GET  /resume                    # Get resume items
GET  /skills/chronology         # Get skills timeline
GET  /projects/timeline         # Get projects timeline
DELETE /projects/{id}           # Delete project
```

---

## Architecture Design

### Directory Structure (Proposed)

```
opentui-react-exp/
├── src/
│   ├── index.tsx                 # Main app entry
│   ├── types.ts                  # Type definitions
│   │
│   ├── api/                      # NEW: API layer
│   │   ├── client.ts             # HTTP client wrapper
│   │   ├── endpoints.ts          # API endpoint functions
│   │   └── types.ts              # API response types
│   │
│   ├── hooks/                    # NEW: Custom hooks
│   │   ├── useApi.ts             # Generic API hook
│   │   ├── useConsent.ts         # Consent state hook
│   │   ├── useAnalysis.ts        # Analysis progress hook
│   │   └── useAppState.ts        # Global app state hook
│   │
│   ├── components/
│   │   ├── screens/              # REORGANIZE: Screen components
│   │   │   ├── Landing.tsx
│   │   │   ├── ConsentScreen.tsx
│   │   │   ├── UserConfigScreen.tsx  # NEW
│   │   │   ├── FileUploadScreen.tsx
│   │   │   ├── ProjectListScreen.tsx
│   │   │   ├── AnalysisScreen.tsx
│   │   │   └── ResumeScreen.tsx
│   │   │
│   │   ├── common/               # NEW: Shared components
│   │   │   ├── TopBar.tsx
│   │   │   ├── BottomBar.tsx
│   │   │   ├── LoadingSpinner.tsx
│   │   │   ├── ErrorBanner.tsx
│   │   │   ├── StatusIndicator.tsx
│   │   │   └── Card.tsx
│   │   │
│   │   └── forms/                # NEW: Form components
│   │       ├── FormField.tsx
│   │       └── FileSelector.tsx
│   │
│   ├── context/                  # NEW: React context
│   │   └── AppContext.tsx        # Global app state
│   │
│   └── utils/                    # NEW: Utilities
│       ├── colors.ts             # Theme colors
│       └── format.ts             # Formatting helpers
│
├── package.json
└── tsconfig.json
```

### Data Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                         AppContext                               │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ State: zipId, userEmail, consentLevel, analysisResult   │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
   ┌─────────┐          ┌─────────┐          ┌─────────┐
   │ Landing │ ───────► │ Consent │ ───────► │UserConfig│
   └─────────┘          └─────────┘          └─────────┘
                              │                     │
                              │ consentLevel        │ userEmail
                              ▼                     ▼
                        ┌───────────┐         ┌───────────┐
                        │FileUpload │ ──────► │ProjectList│
                        └───────────┘         └───────────┘
                              │ zipId               │ selectedDirs
                              │                     ▼
                              │               ┌───────────┐
                              └─────────────► │ Analysis  │
                                              └───────────┘
                                                    │ analysisResult
                                                    ▼
                                              ┌───────────┐
                                              │  Resume   │
                                              └───────────┘
```

---

## Implementation Phases

### Phase 1: Foundation (Days 1-3)

#### 1.1 API Client Layer (`src/api/client.ts`)
- Create `ApiClient` class with `get`, `post`, `put`, `uploadFile`, `delete` methods
- Use `fetch` with `AbortSignal.timeout()` for request timeouts
- Handle errors with custom `ApiError` class
- Base URL from `ARTIFACT_MINER_API_URL` env var (default: `http://127.0.0.1:8000`)

#### 1.2 API Types (`src/api/types.ts`)
Define TypeScript interfaces matching backend responses:
- `ConsentResponse`, `Question`, `UploadResponse`, `DirectoriesResponse`
- `AnalysisResponse`, `Summary`, `ResumeItem`, `ProjectRanking`

#### 1.3 App Context (`src/context/AppContext.tsx`)
Create React context to hold global state:
- `consentLevel`, `userEmail`, `zipId`, `directories`, `selectedDirectories`
- `analysisResult`, `analysisStatus`, `resumeItems`, `summaries`
- Expose setters and `reset()` function

#### 1.4 API Endpoints (`src/api/endpoints.ts`)
Wrap client calls in a typed `api` object:
- `health()`, `getConsent()`, `updateConsent()`
- `getQuestions()`, `submitAnswers()`
- `uploadZip()`, `listDirectories()`
- `runAnalysis()`, `getResume()`, `getSummaries()`
- `getSkillsChronology()`, `getProjectTimeline()`, `deleteProject()`

### Phase 2: Core Screens (Days 4-7)

#### 2.1 UserConfigScreen (NEW)
- Fetch questions from `/questions` on mount
- Render dynamic form fields based on question data
- Submit answers to `/answers`, store email in context
- Handle loading/error/submitting states

#### 2.2 ConsentScreen Updates
- Call `api.updateConsent()` on continue
- Store consent level in app context
- Add saving indicator and error handling

#### 2.3 FileUploadScreen Updates
- Replace mock file list with real filesystem navigation using `fs/promises`
- Navigate directories, filter for `.zip` files
- Upload via `api.uploadZip()`, then fetch directories with `api.listDirectories()`
- Store `zipId` and `directories` in context

#### 2.4 ProjectListScreen Updates
- Read `directories` from app context (no mock data)
- Multi-select with checkboxes, store selected in context
- Pass selected directories to analysis

#### 2.5 AnalysisScreen Updates
- Call `api.runAnalysis(zipId)` on mount
- Show simulated step progression while waiting
- Store result in context, navigate to resume on complete
- Handle error state with retry option

#### 2.6 ResumeScreen Updates
- Fetch `api.getResume()` and `api.getSummaries()` on mount
- Render from context state instead of mock data
- Group items by project, show summaries

### Phase 3: Polish & Testing (Days 8-10)

#### 3.1 Loading States
- Create `LoadingSpinner` component with animated spinner frames
- Use consistently across all screens during API calls

#### 3.2 Error Handling
- Create `ErrorBanner` component with dismiss action
- Add error boundaries around screens
- Show user-friendly error messages

#### 3.3 Export Functionality
- Add `exportToJson()` and `exportToText()` functions to ResumeScreen
- Write files to current directory with timestamp
- Show success/error feedback

---

## UI/UX Improvements

### 1. Enhanced Landing Animation
- Keep the typewriter effect
- Add subtle background pattern or particles
- Smoother CTA button appearance

### 2. Consent Screen Improvements
- Add icons for each option (☁️ vs 🔒)
- Show comparison table more clearly
- Add "Learn More" expandable section

### 3. Better File Browser
- Show file icons based on type
- Breadcrumb navigation
- Recently used paths
- Quick access to common locations (Home, Documents, Downloads)

### 4. Project Selection Enhancements
- Thumbnail/icon for each project type
- Filter/search projects
- Sort by name/size/date
- Bulk select/deselect

### 5. Analysis Progress
- More detailed step descriptions
- Estimated time remaining
- Ability to cancel
- Show what's being analyzed in real-time

### 6. Resume Preview Improvements
- Multiple view modes (compact/detailed)
- Copy individual sections
- Syntax highlighting for code snippets
- Print-friendly export

### Theme Updates
- Primary colors: gold variants (`#FFD700`, `#B8860B`, `#8B7500`)
- Secondary colors: cyan variants (`#00CED1`, `#008B8B`, `#006666`)
- Backgrounds with better contrast: `bgDark`, `bgMedium`, `bgLight`, `bgPanel`
- Text hierarchy: `textPrimary`, `textSecondary`, `textDim`, `textMuted`
- Status colors: success/error/warning/info with dim variants

---

## Testing Strategy

### Unit Tests
- Test `ApiClient` methods (GET, POST, PUT, upload, error handling)
- Test individual hooks (`useAppState`, etc.)
- Mock fetch for isolated testing

### Integration Tests
- Test screen components with mocked API responses
- Verify state updates flow correctly through context
- Test keyboard navigation per screen

### E2E Test Flow
- Full flow: Landing → Consent → Config → Upload → Projects → Analysis → Resume
- Verify data persists across screen transitions
- Test error recovery scenarios

---

## Migration Checklist

### Phase 1: Foundation
- [ ] Create `src/api/client.ts`
- [ ] Create `src/api/types.ts`
- [ ] Create `src/api/endpoints.ts`
- [ ] Create `src/context/AppContext.tsx`
- [ ] Update `src/index.tsx` with AppProvider
- [ ] Test API connectivity

### Phase 2: Core Screens
- [ ] Create `UserConfigScreen.tsx`
- [ ] Update `ConsentScreen.tsx` with API
- [ ] Update `FileUploadScreen.tsx` with real file picker
- [ ] Update `ProjectListScreen.tsx` with API data
- [ ] Update `AnalysisScreen.tsx` with real analysis
- [ ] Update `ResumeScreen.tsx` with API data
- [ ] Update navigation flow in `index.tsx`

### Phase 3: Polish
- [ ] Create `LoadingSpinner.tsx`
- [ ] Create `ErrorBanner.tsx`
- [ ] Add export functionality
- [ ] Improve animations
- [ ] Add keyboard shortcuts help overlay
- [ ] Update theme colors
- [ ] Add proper error handling everywhere

### Phase 4: Testing
- [ ] Write API client unit tests
- [ ] Write screen component tests
- [ ] Write E2E flow test
- [ ] Manual testing of full flow
- [ ] Fix any bugs found

### Phase 5: Documentation
- [ ] Update README with new setup instructions
- [ ] Document environment variables
- [ ] Document keyboard shortcuts
- [ ] Add screenshots/GIFs

---

## Environment Variables

- `ARTIFACT_MINER_API_URL` - Backend API URL (default: `http://127.0.0.1:8000`)
- `ARTIFACT_MINER_TIMEOUT` - Request timeout in ms (default: `30000`)

---

## Running the Migration

1. Start backend: `uv run uvicorn src.artifactminer.api.main:app --reload`
2. In another terminal: `cd opentui-react-exp && bun install && bun run src/index.tsx`

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| API not running | Add clear error message, health check on startup |
| File upload fails | Retry logic, progress indicator, size validation |
| Analysis takes too long | Timeout handling, cancel option, progress updates |
| State lost on navigation | Persist critical state, confirm before destructive actions |
| Terminal size issues | Responsive layouts, minimum size warnings |

---

## Success Criteria

1. ✅ All screens functional with real API data
2. ✅ Full flow works: Landing → Consent → Config → Upload → Projects → Analysis → Resume
3. ✅ Error states handled gracefully
4. ✅ Loading states shown appropriately
5. ✅ Keyboard navigation works on all screens
6. ✅ Export functionality works
7. ✅ Tests pass
8. ✅ No mock data in production flow
