# Engineering Decisions

This document captures the major engineering decisions made while building the
zylabs Research Copilot, the alternatives considered, and the tradeoffs behind
each choice.

## Decision 1: Stream progress by polling the database (SSE-over-DB)

**What I did.** The workflow runs in a background thread and writes a
`workflow_step` row as each node finishes. The SSE endpoint reads new steps from
the database every 0.5s and pushes them to the browser.

**Alternatives considered.**
- *In-memory pub/sub (asyncio queues per session).* Lower latency, no DB polling.
- *WebSockets.* Full duplex, but more complex on both client and server.
- *Plain polling from the frontend.* Simplest, but a worse user experience.

**Tradeoffs.** The DB-backed approach decouples the worker thread from the web
layer entirely: the worker only writes rows, the SSE endpoint only reads them.
This is simpler and more robust (progress survives a page refresh or even a
reconnect, since steps are persisted), at the cost of ~0.5s latency and some
extra reads. For this scope that tradeoff is clearly worth it; an in-memory bus
would be the next step if sub-second latency mattered.

## Decision 2: Structured output via Pydantic instead of prompt-and-parse

**What I did.** The analysis node uses `llm.with_structured_output(ReportSections)`
to force the model to return a typed object with exactly the report fields, and
the quality node uses the same pattern for a `QualityVerdict`.

**Alternatives considered.**
- *Free-text generation + manual parsing/regex.* Flexible but brittle.
- *JSON-mode prompting without a schema.* Better, but still requires hand-written
  validation and error handling.

**Tradeoffs.** Structured output makes the report reliable to store and render —
every field is guaranteed present and typed, which keeps the database schema and
the React components simple. The cost is a little less flexibility in the model's
phrasing and an occasional need to keep the Pydantic schema and prompt in sync.
Given that the report must always contain the same nine sections, the
reliability is the right call.

## Decision 3: Background thread instead of a task queue

**What I did.** `start_workflow` launches a daemon `threading.Thread` that runs
the (synchronous) LangGraph workflow with its own database session, and returns
immediately so the API stays responsive.

**Alternatives considered.**
- *FastAPI `BackgroundTasks`.* Simpler, but tied to the request lifecycle and the
  threadpool, with less control.
- *A real task queue (Celery / RQ / Arq).* Production-grade: retries, multiple
  workers, observability — but heavy setup (a broker like Redis) for a 2-day build.
- *Running the graph synchronously in the request.* Would block the HTTP request
  for ~30–45 seconds, which is unacceptable.

**Tradeoffs.** A thread is the smallest thing that gives non-blocking execution
and isolated DB state, with zero extra infrastructure. It is correct for a single
instance but does not scale across processes/machines and offers no built-in
retry/visibility. The clean separation (runner service + DB persistence) means
swapping in a task queue later is localized to one module.

## Decision 4: Next.js + TypeScript frontend, but backend stays in FastAPI

**What I did.** Built the frontend with Next.js (App Router) + TypeScript +
Tailwind + shadcn/ui, while keeping all application logic in the separate FastAPI
backend. The frontend talks to the backend over HTTP/SSE via a typed API client.

**Alternatives considered.**
- *Plain React + Vite (JavaScript).* Lighter and faster to start, but no type
  safety on the API contract.
- *Next.js with its own API/route handlers.* Tempting for a single deployable,
  but it would duplicate (and conflict with) the assignment-mandated Python
  backend, and split the AI logic across two languages.

**Tradeoffs.** TypeScript gives a compile-time-checked contract between the
frontend and backend (shared `types.ts` mirroring the Pydantic schemas), which
catches mistakes early and documents the API. The cost is a heavier toolchain and
that Next.js's server features (SSR, route handlers) go mostly unused — a
deliberate choice, since the backend must be FastAPI. For an internal,
logged-in dashboard the interactive parts are client components, so SSR adds
little here.

## Decision 5: Multi-query, facet-based research with inline citations

**What I did.** Upgraded the research stage from a single broad Tavily query to a
structured pipeline. The planner emits a typed `ResearchPlan` (a disambiguation
line plus 4-6 targeted queries spread across fixed facets: overview/products,
customers, funding, leadership/hiring, news, competitors/risks). The research
node runs those queries concurrently (thread pool), numbers and de-duplicates
sources, and uses a recency-biased search for the `news` facet. The analysis
node adds inline `[n]` citations tied to real source numbers, and the quality
node returns which facets are weak so a redo re-researches only those facets.

**Alternatives considered.**
- *Keep the single broad query.* Simplest and cheapest, but thin/off-target for
  smaller or ambiguously named companies, and no per-claim verifiability.
- *Sequential multi-query.* Same depth but much slower (latency adds up per call).
- *Re-research everything on each retry.* Simple, but doubles cost for the whole
  report when usually only one or two facets are weak.

**Tradeoffs.** This trades higher per-report cost (several Tavily calls instead
of one) for materially better depth, accuracy, disambiguation, and trust
(citations). Concurrency hides most of the added latency, and the targeted redo
keeps retries cheap. The fixed facet list also lets the quality node refer to
weak areas by name, which is what makes the targeted redo possible.

---

## Bonus — What I'd improve with 2 more weeks

- **Replace threads with a task queue** (Arq/RQ on Redis) for horizontal scaling,
  retries with backoff, and proper job visibility.
- **LangGraph checkpointing** (SqliteSaver/Postgres) keyed by session id, enabling
  true resume-after-crash and partial re-runs of single nodes.
- **Per-claim verification UI** that surfaces, for each sentence, the exact source
  snippet behind it (building on the inline citations already shipped).
- **Cost & reliability hardening:** caching of repeated company lookups, per-user
  rate limits, model fallbacks (`with_fallbacks`), and structured cost logging.
- **Tests:** unit tests for each node with a mocked LLM/search, and an API test
  suite, so the workflow can be changed with confidence.
- **Auth & multi-tenancy** so multiple sellers can use it with separated data.
