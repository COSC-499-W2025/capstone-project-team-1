# OpenTUI React Experimental Client

This package contains an experimental terminal UI for Artifact Miner built with React and OpenTUI. It explores an alternative workflow for consent, ZIP intake, project analysis, and resume generation alongside the main FastAPI backend and Textual TUI in the repository root.

## What It Does

- renders a React-driven terminal experience with OpenTUI
- talks to the Artifact Miner backend over HTTP
- exercises the local resume-generation flow exposed under `/local-llm/*`
- includes mock data and tests for UI iteration while the backend APIs continue to evolve

## Prerequisites

- Bun 1.x
- the main Artifact Miner backend running locally

By default the client targets `http://127.0.0.1:8000`. Override that with `ARTIFACT_MINER_API_URL` if your backend is running elsewhere. You can also set `ARTIFACT_MINER_TIMEOUT` to adjust the request timeout in milliseconds.

## Install

```bash
bun install
```

## Run

From this directory:

```bash
bun run src/index.tsx
```

For auto-reload during development:

```bash
bun run dev
```

## Test And Lint

```bash
bun test
bun run lint
```

## Relationship To The Main Project

This client is not the primary Artifact Miner interface. The repository root contains the backend API and the Textual TUI that make up the main application. Use this package when you want to experiment with the React/OpenTUI flow or iterate on terminal UX patterns without changing the primary TUI implementation.
