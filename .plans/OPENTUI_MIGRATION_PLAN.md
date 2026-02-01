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

#### 1.1 Create API Client Layer

```typescript
// src/api/client.ts
const API_BASE = process.env.ARTIFACT_MINER_API_URL || 'http://127.0.0.1:8000';

export class ApiClient {
  private baseUrl: string;
  private timeout: number;

  constructor(baseUrl = API_BASE, timeout = 30000) {
    this.baseUrl = baseUrl;
    this.timeout = timeout;
  }

  async get<T>(path: string, params?: Record<string, string>): Promise<T> {
    const url = new URL(path, this.baseUrl);
    if (params) {
      Object.entries(params).forEach(([k, v]) => url.searchParams.set(k, v));
    }
    const response = await fetch(url.toString(), {
      signal: AbortSignal.timeout(this.timeout),
    });
    if (!response.ok) throw new ApiError(response.status, await response.text());
    return response.json();
  }

  async post<T>(path: string, body?: unknown): Promise<T> {
    const response = await fetch(`${this.baseUrl}${path}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: body ? JSON.stringify(body) : undefined,
      signal: AbortSignal.timeout(this.timeout),
    });
    if (!response.ok) throw new ApiError(response.status, await response.text());
    return response.json();
  }

  async uploadFile<T>(path: string, file: Buffer, filename: string): Promise<T> {
    const formData = new FormData();
    formData.append('file', new Blob([file]), filename);
    const response = await fetch(`${this.baseUrl}${path}`, {
      method: 'POST',
      body: formData,
      signal: AbortSignal.timeout(this.timeout * 2), // Longer timeout for uploads
    });
    if (!response.ok) throw new ApiError(response.status, await response.text());
    return response.json();
  }

  async put<T>(path: string, body?: unknown): Promise<T> {
    const response = await fetch(`${this.baseUrl}${path}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: body ? JSON.stringify(body) : undefined,
      signal: AbortSignal.timeout(this.timeout),
    });
    if (!response.ok) throw new ApiError(response.status, await response.text());
    return response.json();
  }
}
```

#### 1.2 Define API Types

```typescript
// src/api/types.ts
export interface ConsentResponse {
  consent_level: 'full' | 'no_llm' | 'none';
  accepted_at: string | null;
}

export interface Question {
  id: number;
  key: string;
  question_text: string;
}

export interface UploadResponse {
  zip_id: number;
  filename: string;
}

export interface DirectoriesResponse {
  directories: string[];
}

export interface AnalysisResponse {
  repos_found: number;
  summaries: Summary[];
  rankings?: ProjectRanking[];
}

export interface Summary {
  id: number;
  repo_path: string;
  summary_text: string;
  created_at: string;
}

export interface ResumeItem {
  id: number;
  title: string;
  content: string;
  project_name?: string;
  category?: string;
}

export interface ProjectRanking {
  name: string;
  score: number;
}
```

#### 1.3 Create App Context

```typescript
// src/context/AppContext.tsx
import { createContext, useContext, useState, ReactNode } from 'react';

interface AppState {
  // Auth/Config
  consentLevel: 'full' | 'no_llm' | 'none';
  userEmail: string | null;
  
  // Upload
  zipId: number | null;
  zipPath: string | null;
  directories: string[];
  selectedDirectories: string[];
  
  // Analysis
  analysisResult: AnalysisResponse | null;
  analysisStatus: 'idle' | 'running' | 'complete' | 'error';
  
  // Resume
  resumeItems: ResumeItem[];
  summaries: Summary[];
}

interface AppContextType {
  state: AppState;
  setConsentLevel: (level: 'full' | 'no_llm' | 'none') => void;
  setUserEmail: (email: string) => void;
  setZipId: (id: number) => void;
  setDirectories: (dirs: string[]) => void;
  setSelectedDirectories: (dirs: string[]) => void;
  setAnalysisResult: (result: AnalysisResponse) => void;
  setResumeData: (items: ResumeItem[], summaries: Summary[]) => void;
  reset: () => void;
}

const AppContext = createContext<AppContextType | null>(null);

export function AppProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<AppState>(initialState);
  
  // ... implement setters
  
  return (
    <AppContext.Provider value={{ state, ...setters }}>
      {children}
    </AppContext.Provider>
  );
}

export function useAppState() {
  const context = useContext(AppContext);
  if (!context) throw new Error('useAppState must be used within AppProvider');
  return context;
}
```

#### 1.4 Create API Endpoint Functions

```typescript
// src/api/endpoints.ts
import { ApiClient } from './client';
import type * as T from './types';

const client = new ApiClient();

export const api = {
  // Health
  health: () => client.get<{ status: string }>('/health'),
  
  // Consent
  getConsent: () => client.get<T.ConsentResponse>('/consent'),
  updateConsent: (level: string) => 
    client.put<T.ConsentResponse>('/consent', { consent_level: level }),
  
  // Questions
  getQuestions: () => client.get<T.Question[]>('/questions'),
  submitAnswers: (answers: Record<string, string>) =>
    client.post<T.Question[]>('/answers', { answers }),
  
  // Upload
  uploadZip: (file: Buffer, filename: string) =>
    client.uploadFile<T.UploadResponse>('/zip/upload', file, filename),
  listDirectories: (zipId: number) =>
    client.get<T.DirectoriesResponse>(`/zip/${zipId}/directories`),
  
  // Analysis
  runAnalysis: (zipId: number) =>
    client.post<T.AnalysisResponse>(`/analyze/${zipId}`),
  
  // Results
  getResume: (projectId?: number) =>
    client.get<T.ResumeItem[]>('/resume', projectId ? { project_id: String(projectId) } : undefined),
  getSummaries: (email: string) =>
    client.get<T.Summary[]>('/summaries', { user_email: email }),
  getSkillsChronology: () => client.get<T.SkillChronology[]>('/skills/chronology'),
  getProjectTimeline: () => client.get<T.ProjectTimeline[]>('/projects/timeline'),
  
  // Management
  deleteProject: (projectId: number) =>
    client.delete<{ deleted_id: number }>(`/projects/${projectId}`),
};
```

### Phase 2: Core Screens (Days 4-7)

#### 2.1 Create UserConfigScreen (NEW)

```typescript
// src/components/screens/UserConfigScreen.tsx
import { useKeyboard } from '@opentui/react';
import { useState, useEffect } from 'react';
import { api } from '../../api/endpoints';
import { useAppState } from '../../context/AppContext';
import { theme } from '../../types';
import { TopBar } from '../common/TopBar';

interface UserConfigScreenProps {
  onContinue: () => void;
  onBack: () => void;
}

export function UserConfigScreen({ onContinue, onBack }: UserConfigScreenProps) {
  const { setUserEmail } = useAppState();
  const [questions, setQuestions] = useState<Question[]>([]);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [focusIndex, setFocusIndex] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    loadQuestions();
  }, []);

  async function loadQuestions() {
    try {
      setLoading(true);
      const data = await api.getQuestions();
      setQuestions(data);
      // Initialize answers
      const initial: Record<string, string> = {};
      data.forEach(q => { initial[q.key] = ''; });
      setAnswers(initial);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load questions');
    } finally {
      setLoading(false);
    }
  }

  async function handleSubmit() {
    try {
      setSubmitting(true);
      await api.submitAnswers(answers);
      if (answers.email) {
        setUserEmail(answers.email);
      }
      onContinue();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to submit');
    } finally {
      setSubmitting(false);
    }
  }

  useKeyboard((key) => {
    if (key.name === 'escape') onBack();
    if (key.name === 'tab') {
      setFocusIndex(i => (i + 1) % (questions.length + 1)); // +1 for submit button
    }
    if (key.name === 'return' && focusIndex === questions.length) {
      handleSubmit();
    }
  });

  if (loading) {
    return (
      <box flexGrow={1} alignItems="center" justifyContent="center">
        <text fg={theme.cyan}>Loading questions...</text>
      </box>
    );
  }

  return (
    <box flexGrow={1} flexDirection="column" backgroundColor={theme.bgDark}>
      <TopBar
        step="Configuration"
        title="User Setup"
        description="Please answer a few questions to personalize your experience"
      />
      
      <box flexGrow={1} flexDirection="column" padding={2} gap={2}>
        {questions.map((q, i) => (
          <box key={q.key} flexDirection="column" gap={1}>
            <text fg={theme.textSecondary}>{q.question_text}</text>
            <input
              value={answers[q.key] || ''}
              onChange={(val) => setAnswers(prev => ({ ...prev, [q.key]: val }))}
              focused={focusIndex === i}
              placeholder={`Enter ${q.key}...`}
              backgroundColor={theme.bgMedium}
              width={40}
            />
          </box>
        ))}
        
        {error && (
          <box border borderColor={theme.error} padding={1}>
            <text fg={theme.error}>{error}</text>
          </box>
        )}
        
        <box
          border
          borderColor={focusIndex === questions.length ? theme.gold : theme.textDim}
          padding={1}
          onMouseDown={handleSubmit}
        >
          <text fg={theme.gold}>
            {submitting ? 'Submitting...' : 'Continue →'}
          </text>
        </box>
      </box>
    </box>
  );
}
```

#### 2.2 Update ConsentScreen with API

```typescript
// Updates to ConsentScreen.tsx
import { api } from '../../api/endpoints';
import { useAppState } from '../../context/AppContext';

export function ConsentScreen({ onContinue, onBack }: ConsentScreenProps) {
  const { setConsentLevel } = useAppState();
  const [selected, setSelected] = useState<Selection>('offline');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleContinue() {
    try {
      setSaving(true);
      const level = selected === 'cloud' ? 'full' : 'no_llm';
      await api.updateConsent(level);
      setConsentLevel(level);
      onContinue(selected === 'cloud');
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to save consent');
    } finally {
      setSaving(false);
    }
  }

  useKeyboard((key) => {
    if (key.name === 'return') handleContinue();
    // ... rest of keyboard handling
  });

  // ... rest of component
}
```

#### 2.3 Update FileUploadScreen with Real File Picker

```typescript
// src/components/screens/FileUploadScreen.tsx
import { readdir, stat, readFile } from 'fs/promises';
import { join, dirname, basename } from 'path';
import { homedir } from 'os';

interface FileEntry {
  name: string;
  path: string;
  isDirectory: boolean;
  size?: number;
}

export function FileUploadScreen({ onSubmit, onBack }: FileUploadProps) {
  const { setZipId, setDirectories } = useAppState();
  const [currentPath, setCurrentPath] = useState(homedir());
  const [entries, setEntries] = useState<FileEntry[]>([]);
  const [selectedIndex, setSelectedIndex] = useState(0);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadDirectory(currentPath);
  }, [currentPath]);

  async function loadDirectory(path: string) {
    try {
      const items = await readdir(path);
      const entriesWithStats = await Promise.all(
        items.map(async (name) => {
          const fullPath = join(path, name);
          const stats = await stat(fullPath);
          return {
            name,
            path: fullPath,
            isDirectory: stats.isDirectory(),
            size: stats.size,
          };
        })
      );
      // Sort: directories first, then files
      entriesWithStats.sort((a, b) => {
        if (a.isDirectory && !b.isDirectory) return -1;
        if (!a.isDirectory && b.isDirectory) return 1;
        return a.name.localeCompare(b.name);
      });
      // Add parent directory option
      setEntries([
        { name: '..', path: dirname(path), isDirectory: true },
        ...entriesWithStats,
      ]);
      setSelectedIndex(0);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to read directory');
    }
  }

  async function handleSelect() {
    const entry = entries[selectedIndex];
    if (!entry) return;
    
    if (entry.isDirectory) {
      setCurrentPath(entry.path);
    } else if (entry.name.endsWith('.zip')) {
      await uploadFile(entry.path);
    }
  }

  async function uploadFile(filePath: string) {
    try {
      setUploading(true);
      const fileBuffer = await readFile(filePath);
      const result = await api.uploadZip(fileBuffer, basename(filePath));
      setZipId(result.zip_id);
      
      // Fetch directories
      const dirsResult = await api.listDirectories(result.zip_id);
      const cleanedDirs = dirsResult.directories
        .filter(d => !d.startsWith('__MACOSX') && !d.includes('/._'))
        .map(d => d.endsWith('/') ? d.slice(0, -1) : d);
      setDirectories(cleanedDirs);
      
      onSubmit(filePath);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Upload failed');
    } finally {
      setUploading(false);
    }
  }

  useKeyboard((key) => {
    if (key.name === 'escape') onBack();
    if (key.name === 'up' || key.name === 'k') {
      setSelectedIndex(i => Math.max(0, i - 1));
    }
    if (key.name === 'down' || key.name === 'j') {
      setSelectedIndex(i => Math.min(entries.length - 1, i + 1));
    }
    if (key.name === 'return') handleSelect();
  });

  return (
    <box flexGrow={1} flexDirection="column" backgroundColor={theme.bgDark}>
      <TopBar
        step="Step 1"
        title="Select ZIP File"
        description={currentPath}
      />
      
      <box flexGrow={1} flexDirection="row" padding={1} gap={1}>
        {/* File list */}
        <box flexGrow={1} border borderColor={theme.gold} flexDirection="column">
          <select
            options={entries.map(e => ({
              name: e.isDirectory ? `📁 ${e.name}` : `📄 ${e.name}`,
              description: e.isDirectory ? 'Directory' : formatSize(e.size),
              value: e.path,
            }))}
            selectedIndex={selectedIndex}
            onChange={(i) => setSelectedIndex(i)}
            onSelect={() => handleSelect()}
            focused
            height={20}
            showScrollIndicator
          />
        </box>
        
        {/* Details panel */}
        <box width={30} border borderColor={theme.textDim} padding={1} flexDirection="column">
          {uploading ? (
            <text fg={theme.cyan}>Uploading...</text>
          ) : error ? (
            <text fg={theme.error}>{error}</text>
          ) : (
            <text fg={theme.textDim}>
              Select a .zip file to upload
            </text>
          )}
        </box>
      </box>
    </box>
  );
}
```

#### 2.4 Update ProjectListScreen with API Data

```typescript
// src/components/screens/ProjectListScreen.tsx
export function ProjectListScreen({ onContinue, onBack }: ProjectListProps) {
  const { state, setSelectedDirectories } = useAppState();
  const [selectedIndices, setSelectedIndices] = useState<Set<number>>(new Set());
  
  const directories = state.directories;

  function toggleSelection(index: number) {
    setSelectedIndices(prev => {
      const next = new Set(prev);
      if (next.has(index)) {
        next.delete(index);
      } else {
        next.add(index);
      }
      return next;
    });
  }

  function handleContinue() {
    const selected = Array.from(selectedIndices).map(i => directories[i]);
    setSelectedDirectories(selected);
    onContinue();
  }

  // ... render with checkboxes for multi-select
}
```

#### 2.5 Update AnalysisScreen with Real API

```typescript
// src/components/screens/AnalysisScreen.tsx
export function AnalysisScreen({ onComplete, onBack }: AnalysisProps) {
  const { state, setAnalysisResult } = useAppState();
  const [status, setStatus] = useState<'idle' | 'running' | 'complete' | 'error'>('idle');
  const [currentStep, setCurrentStep] = useState(0);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (state.zipId) {
      runAnalysis();
    }
  }, [state.zipId]);

  async function runAnalysis() {
    if (!state.zipId) return;
    
    try {
      setStatus('running');
      
      // Simulate step progression while waiting for API
      const stepInterval = setInterval(() => {
        setCurrentStep(s => Math.min(s + 1, analysisSteps.length - 1));
      }, 800);
      
      const result = await api.runAnalysis(state.zipId);
      
      clearInterval(stepInterval);
      setCurrentStep(analysisSteps.length);
      setAnalysisResult(result);
      setStatus('complete');
      
      setTimeout(onComplete, 1000);
    } catch (e) {
      setStatus('error');
      setError(e instanceof Error ? e.message : 'Analysis failed');
    }
  }

  // ... render with real progress
}
```

#### 2.6 Update ResumeScreen with API Data

```typescript
// src/components/screens/ResumeScreen.tsx
export function ResumeScreen({ onBack, onRestart }: ResumePreviewProps) {
  const { state, setResumeData } = useAppState();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadResumeData();
  }, []);

  async function loadResumeData() {
    try {
      setLoading(true);
      const [resumeItems, summaries] = await Promise.all([
        api.getResume(),
        state.userEmail ? api.getSummaries(state.userEmail) : Promise.resolve([]),
      ]);
      setResumeData(resumeItems, summaries);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load resume data');
    } finally {
      setLoading(false);
    }
  }

  // ... render with real data from state.resumeItems and state.summaries
}
```

### Phase 3: Polish & Testing (Days 8-10)

#### 3.1 Add Loading States Component

```typescript
// src/components/common/LoadingSpinner.tsx
const spinnerFrames = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏'];

export function LoadingSpinner({ message = 'Loading...' }: { message?: string }) {
  const [frame, setFrame] = useState(0);

  useEffect(() => {
    const interval = setInterval(() => {
      setFrame(f => (f + 1) % spinnerFrames.length);
    }, 80);
    return () => clearInterval(interval);
  }, []);

  return (
    <box flexDirection="row" gap={1} alignItems="center">
      <text fg={theme.cyan}>{spinnerFrames[frame]}</text>
      <text fg={theme.textSecondary}>{message}</text>
    </box>
  );
}
```

#### 3.2 Add Error Banner Component

```typescript
// src/components/common/ErrorBanner.tsx
export function ErrorBanner({ 
  error, 
  onDismiss 
}: { 
  error: string; 
  onDismiss?: () => void;
}) {
  return (
    <box
      border
      borderColor={theme.error}
      backgroundColor={theme.bgMedium}
      padding={1}
      flexDirection="row"
      justifyContent="space-between"
    >
      <text fg={theme.error}>⚠ {error}</text>
      {onDismiss && (
        <box onMouseDown={onDismiss}>
          <text fg={theme.textDim}>[x]</text>
        </box>
      )}
    </box>
  );
}
```

#### 3.3 Add Export Functionality to Resume

```typescript
// Add to ResumeScreen
import { writeFile } from 'fs/promises';
import { join } from 'path';

async function exportToJson() {
  const data = {
    generatedAt: new Date().toISOString(),
    resumeItems: state.resumeItems,
    summaries: state.summaries,
  };
  const path = join(process.cwd(), `resume_${Date.now()}.json`);
  await writeFile(path, JSON.stringify(data, null, 2));
  return path;
}

async function exportToText() {
  let content = '# Generated Resume\n\n';
  
  // Group by project
  const grouped = groupByProject(state.resumeItems);
  for (const [project, items] of Object.entries(grouped)) {
    content += `## ${project || 'General'}\n\n`;
    for (const item of items) {
      content += `### ${item.title}\n${item.content}\n\n`;
    }
  }
  
  const path = join(process.cwd(), `resume_${Date.now()}.txt`);
  await writeFile(path, content);
  return path;
}
```

---

## State Management

### Global State Shape

```typescript
interface AppState {
  // Flow control
  currentScreen: Screen;
  
  // User configuration
  consentLevel: 'full' | 'no_llm' | 'none';
  userEmail: string | null;
  userAnswers: Record<string, string>;
  
  // Upload state
  zipId: number | null;
  zipPath: string | null;
  directories: string[];
  selectedDirectories: string[];
  
  // Analysis state
  analysisStatus: 'idle' | 'running' | 'complete' | 'error';
  analysisProgress: number;
  analysisResult: AnalysisResponse | null;
  
  // Results
  resumeItems: ResumeItem[];
  summaries: Summary[];
  skillsTimeline: SkillChronology[];
  projectsTimeline: ProjectTimeline[];
  
  // UI state
  error: string | null;
  loading: boolean;
}
```

### Actions

```typescript
type AppAction =
  | { type: 'SET_SCREEN'; screen: Screen }
  | { type: 'SET_CONSENT'; level: ConsentLevel }
  | { type: 'SET_USER_EMAIL'; email: string }
  | { type: 'SET_ANSWERS'; answers: Record<string, string> }
  | { type: 'SET_ZIP_ID'; id: number }
  | { type: 'SET_DIRECTORIES'; dirs: string[] }
  | { type: 'SET_SELECTED_DIRS'; dirs: string[] }
  | { type: 'START_ANALYSIS' }
  | { type: 'UPDATE_ANALYSIS_PROGRESS'; progress: number }
  | { type: 'COMPLETE_ANALYSIS'; result: AnalysisResponse }
  | { type: 'ANALYSIS_ERROR'; error: string }
  | { type: 'SET_RESUME_DATA'; items: ResumeItem[]; summaries: Summary[] }
  | { type: 'SET_ERROR'; error: string | null }
  | { type: 'RESET' };
```

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

```typescript
// Enhanced theme
export const theme = {
  // Primary: Gold
  gold: '#FFD700',
  goldDark: '#B8860B',
  goldDim: '#8B7500',
  goldGlow: 'rgba(255, 215, 0, 0.3)',

  // Secondary: Cyan
  cyan: '#00CED1',
  cyanDark: '#008B8B',
  cyanDim: '#006666',
  cyanGlow: 'rgba(0, 206, 209, 0.3)',

  // Backgrounds with better contrast
  bgDark: '#0a0a0f',
  bgMedium: '#1a1a2e',
  bgLight: '#2a2a4e',
  bgPanel: '#16162a',

  // Text with better hierarchy
  textPrimary: '#FFFFFF',
  textSecondary: '#B0B0C0',
  textDim: '#606080',
  textMuted: '#404060',

  // Status colors
  success: '#32CD32',
  successDim: '#228B22',
  error: '#FF4444',
  errorDim: '#CC3333',
  warning: '#FFA500',
  warningDim: '#CC8400',
  info: '#4169E1',
  infoDim: '#3355BB',
} as const;
```

---

## Testing Strategy

### Unit Tests

```typescript
// src/__tests__/api/client.test.ts
import { describe, it, expect, mock } from 'bun:test';
import { ApiClient } from '../../api/client';

describe('ApiClient', () => {
  it('should make GET requests', async () => {
    const client = new ApiClient('http://localhost:8000');
    // Mock fetch...
  });
  
  it('should handle errors', async () => {
    // Test error handling...
  });
});
```

### Integration Tests

```typescript
// src/__tests__/screens/ConsentScreen.test.tsx
import { describe, it, expect } from 'bun:test';
import { createTestRenderer } from '@opentui/react/testing';
import { ConsentScreen } from '../../components/screens/ConsentScreen';

describe('ConsentScreen', () => {
  it('should render consent options', async () => {
    const renderer = createTestRenderer();
    // Render and test...
  });
  
  it('should save consent on continue', async () => {
    // Test API integration...
  });
});
```

### E2E Test Flow

```typescript
// src/__tests__/e2e/full-flow.test.ts
describe('Full Application Flow', () => {
  it('should complete full upload and analysis flow', async () => {
    // 1. Start at Landing
    // 2. Navigate to Consent, select option
    // 3. Fill UserConfig
    // 4. Upload ZIP
    // 5. Select projects
    // 6. Run analysis
    // 7. View resume
  });
});
```

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

```bash
# .env
ARTIFACT_MINER_API_URL=http://127.0.0.1:8000
ARTIFACT_MINER_TIMEOUT=30000
```

---

## Running the Migration

```bash
# 1. Start the backend API
cd /path/to/capstone-project-team-1
uv run uvicorn src.artifactminer.api.main:app --reload

# 2. In another terminal, run the OpenTUI app
cd opentui-react-exp
bun install
bun run src/index.tsx
```

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
