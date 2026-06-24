# Architecture

## Overview

Project01 Research Copilot is a three-tier application: a React frontend, a
FastAPI backend, and a LangGraph AI workflow, with SQLite for persistence.

```
┌─────────────────────────────────────────────────────────────┐
│  FRONTEND (Next.js + TypeScript + Tailwind + shadcn/ui)     │
│  Home (create + history) · Detail (progress, report, chat)  │
└───────────────────────────┬─────────────────────────────────┘
                            │  HTTP (JSON) + SSE
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  BACKEND (FastAPI)                                           │
│  api/sessions  ·  api/workflow  ·  api/chat                  │
│  services/runner   services/chat                            │
└──────────────┬───────────────────────────┬──────────────────┘
               │                            │
               ▼                            ▼
┌──────────────────────────┐   ┌────────────────────────────────┐
│  AI WORKFLOW (LangGraph) │   │  STORAGE (SQLite + SQLAlchemy) │
│  planner → research →    │   │  sessions · reports            │
│  analysis → quality →    │   │  workflow_steps · chat_messages│
│  report_gen  (+ loop)    │   └────────────────────────────────┘
│      │                   │
│      ├─► OpenAI (LLM)    │
│      └─► Tavily (search) │
└──────────────────────────┘
```

## Layers

### Frontend — Next.js (React) + TypeScript + Tailwind + shadcn/ui
A React app built on the Next.js App Router with two routes: the home page
(session creation form + history list) and the session detail page at
`/sessions/[id]` (live workflow progress, the structured report, and a follow-up
chat panel). React satisfies the assignment requirement; Next.js + TypeScript
add a typed, production-grade structure. A typed API client (`lib/api.ts`) with
shared types (`lib/types.ts`) mirrors the backend schemas so the
frontend/backend contract is checked at compile time. Tailwind + shadcn/ui give
an accessible, consistent component system quickly. The interactive pieces (SSE
progress stream, chat) are client components; the backend is reached directly
over HTTP/SSE using `NEXT_PUBLIC_API_BASE` (CORS is enabled on the backend).
Notably, Next.js's server/API features are intentionally unused here because the
assignment mandates a separate FastAPI backend.

### Backend — Python + FastAPI
FastAPI exposes a small REST API organized around the research session resource.
It was chosen for its first-class async support (important for the SSE progress
stream), automatic request validation via Pydantic, and auto-generated API docs.
Business logic lives in a thin service layer (`services/runner.py`,
`services/chat.py`) so the route handlers stay simple.

### AI Workflow — LangGraph + LangChain
The core of the product. A `StateGraph` threads a shared `GraphState` through
five nodes. LangGraph was mandatory and is the right tool: it makes the
multi-step process explicit, supports conditional routing (the quality-retry
loop), and gives intermediate outputs we can stream. LangChain provides the LLM
abstraction, structured output (Pydantic), and the Tavily search integration.

### Storage — SQLite + SQLAlchemy
SQLite is a zero-setup, single-file database — ideal for this scope while still
being a real relational store. SQLAlchemy maps four tables (sessions, reports,
workflow_steps, chat_messages) to Python objects. Swapping to Postgres later is
a one-line `DATABASE_URL` change.

## Data Flow (user input → final report)

1. The user submits the create-session form. The frontend calls
   `POST /api/sessions`, which stores a session row (`status = pending`).
2. The frontend immediately calls `POST /api/sessions/{id}/run`. The backend
   starts the LangGraph workflow in a background thread and returns right away.
3. The workflow runs node by node. Each node reads and updates the shared state:
   - **planner** decides what to research based on the objective.
   - **research** queries Tavily and collects notes + source URLs.
   - **analysis** uses an LLM with structured output to fill the 8 report sections.
   - **quality_check** judges completeness; if weak (and under the retry cap) the
     graph routes back to **research**.
   - **report_gen** attaches the sources and finalizes the report.
   Each node persists a `workflow_step` row as it completes.
4. The frontend opens an SSE connection to `GET /api/sessions/{id}/stream`,
   which reads new steps from the database and pushes them to the browser live.
5. On completion the report is saved (`reports` table) and the session is marked
   `completed`. The frontend fetches and renders the report.
6. Follow-up questions hit `POST /api/sessions/{id}/chat`. The chat service
   rebuilds the message list (system prompt + report context + prior turns + the
   new question), calls the LLM, and persists both messages.

## State Shape (LangGraph)

`GraphState` carries: the inputs (company, website, objective), the planner's
plan, research notes and sources, the report dict, quality-loop control fields
(`quality_ok`, `quality_feedback`, `attempts`), an append-only `steps` log
(using an `operator.add` reducer), and an `error` field.

## Reliability & Recoverability

- Every node is wrapped in `try/except`; a failure records an error in the state
  and a `failed` step rather than crashing the run.
- The quality loop is bounded by `MAX_ATTEMPTS` so it can never loop forever.
- Research merges and de-duplicates sources across retries, so a poor retry can
  never wipe out good results from an earlier pass.
- The workflow runner catches crashes and marks the session `failed` with the
  error message, which the UI surfaces.

## Notable Tradeoffs & Constraints

- **Background thread vs. task queue.** The workflow runs in a Python thread for
  simplicity. This is fine for a single instance but would need a real task
  queue (e.g. Celery/RQ) to scale horizontally.
- **SSE-over-database.** Progress is streamed by polling the DB every 0.5s
  rather than an in-memory pub/sub. This is simple and survives restarts, at the
  cost of a small latency and some DB reads.
- **SQLite.** Great for development and a single node; it serializes writes, so a
  production deployment with concurrency would move to Postgres.
- **Quality judge strictness.** The LLM quality check is intentionally strict, so
  it often triggers one retry. This demonstrates the loop but adds latency/cost;
  the threshold could be tuned.
