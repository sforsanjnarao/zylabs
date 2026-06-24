# Non-Functional Requirements

These targets are stated honestly for **the current build** (a single FastAPI
instance, SQLite, a threaded workflow runner, no auth) alongside the
**production target** and the reason behind each.

> The "current" performance numbers below are **engineering estimates, not
> load-tested benchmarks.** They reflect the expected ceilings of this
> architecture (synchronous SQLAlchemy + SQLite + a single uvicorn worker), and
> the point is to show which levers move them — not to claim measured precision.

| Area | Current (this build) | Target (production) | Why |
| --- | --- | --- | --- |
| **API response time** | CRUD < **~200 ms**; chat < **~3 s**; full report **30–60 s** (async, SSE-streamed — not one blocking call) | CRUD < 100 ms | Report time is dominated by multiple OpenAI + Tavily calls plus the quality-retry loop, so it runs in a background thread instead of blocking the request. |
| **Page load time** | < **~2 s** (estimate) | < 1 s | Next.js App Router; pages are client components hitting a local API. |
| **Scalability — users** | ~**10–20** concurrent browsing; ~**5–10** concurrent workflow runs (estimate) | 1000s | The threaded workflow plus SQLite's write serialization is the ceiling; scaling out needs a task queue + Postgres. |
| **Scalability — req/sec** | ~**200 rps** on simple endpoints assumed for a single worker (**not benchmarked**); workflow throughput bounded by **OpenAI/Tavily rate limits** | Horizontal via multiple workers | The external API limits, not the app code, are the real cap on workflow throughput. |
| **Availability — uptime** | **Best-effort, no HA** (single instance, single DB file). `/health` exists but is **liveness-only** — it returns a static OK and does **not** verify DB/dependency connectivity | **99.9%** | HA needs multiple instances + a managed DB + health-checked deploys, and the health check should be deepened to probe the DB. |
| **Reliability — data-loss tolerance** | **Low**; sessions/reports/steps/chat are persisted and survive restarts, but there are **no backups** (single SQLite file) | Near-zero | The workflow is *recoverable* (each step is persisted) but not *resumable* mid-run. LangGraph checkpointing + Postgres point-in-time backups close both gaps. |
| **Reliability — retry policy** | LLM calls: **2 retries** with backoff (60 s timeout); workflow quality loop bounded at **`MAX_ATTEMPTS = 2`**; every node wrapped in try/except → records a `failed` step instead of crashing | Add automatic re-run of failed jobs | Bounded retries prevent infinite loops and runaway cost while still self-correcting. |
| **Reliability — concurrency failure mode** | Under concurrent writes SQLite can raise **`database is locked` (SQLITE_BUSY)**; the threaded runner each open their own DB session, so heavy parallel runs are the risk | Postgres (row-level locking, no global write lock) | This is the concrete symptom of SQLite's write serialization listed above, called out so it isn't a surprise under load. |
| **Security — input validation** | Request bodies validated by **Pydantic**; `company_name` enforced `min_length=1` + a validator rejecting whitespace-only names; malformed bodies return **422** | Add payload size limits + stricter URL validation | Basic validation is implemented and prevents empty/garbage sessions. |
| **Security — CORS** | Restricted to **explicit configured origins** (`CORS_ORIGINS` in `.env`, default `localhost:3000`) — **no wildcard**, which is also required because a wildcard is invalid alongside `allow_credentials` | Lock to the deployed frontend origin(s) only | Implemented correctly; just needs the production origin set at deploy time. |
| **Security — rate limiting / abuse** | **None** — no per-IP or per-user limits on any endpoint, including the cost-bearing `/run` and `/chat` | Per-user/IP rate limits + quotas (e.g. SlowAPI / gateway) | This is the biggest **cost-abuse** gap: an unauthenticated caller could trigger unlimited paid LLM/search runs. |
| **Security — auth** | **None** (single-user / local) | JWT/OAuth (e.g. Clerk/Auth0) + per-user data scoping | Also documented as a weakness in `product-improvements.md`. |
| **Security — encryption** | In transit: **terminated at the deploy/proxy layer (HTTPS)** — local dev is plain HTTP; at rest: **none** (plaintext SQLite); secrets kept in `.env` (gitignored, never committed) | DB-at-rest encryption / managed DB encryption | Secrets are read from environment variables and excluded from git — verified. |
| **Security — data privacy** | Company inputs and research notes are sent to **third parties (OpenAI, Tavily)**; no data-processing controls or redaction | A clear data-processing policy, vendor DPAs, opt-out, and PII redaction before egress | For a B2B sales tool this is a real compliance NFR, stated honestly rather than ignored. |
| **Usability / accessibility** | **Responsive** layout; UI built on **shadcn/ui (Radix primitives)** which are keyboard- and screen-reader-accessible by default; clear loading (skeletons/“Thinking…”), error (toasts), and empty states | Formal a11y audit (WCAG AA), focus management, reduced-motion support | Accessibility is largely inherited from the component library; not yet independently audited. |
| **Observability — logging** | **Python stdlib `logging`**, per-component loggers (`project01.workflow`, `project01.runner`, `project01.api`, `project01.chat`), full tracebacks on failure paths | Ship logs to an aggregator (Loki/Datadog) + request IDs | Structured logging on failure paths is already in place. |
| **Observability — monitoring** | **`/health` endpoint only**; no metrics or tracing | Prometheus metrics (latency, error rate, per-node duration, **token cost**) + alerting | Per-node and token-cost metrics matter because LLM/search cost is the #1 scaling risk. |
| **Cost** | No explicit budget or per-report cost tracking; each report = several LLM + search calls, **multiplied by the retry loop** | Track cost/report; cap retries; cache repeated lookups | Tied directly to the rate-limiting gap above — together they bound spend. |
| **Maintainability — test coverage** | **0%** (acknowledged in `engineering-decisions.md`) | Per-node unit tests with a mocked LLM/search + an API test suite | Mocked-LLM node tests are the highest-leverage addition for safe iteration. |
| **Maintainability — deployment** | Not yet deployed; **env-based config**, SQLite → Postgres via a one-line `DATABASE_URL` change | Docker + CI/CD (GitHub Actions): backend on Render/Fly, frontend on Vercel | The clean service split (FastAPI backend, Next.js frontend) already supports independent deploys. |

## Reading these honestly

The biggest gaps — no auth, no rate limiting, no tests, no HA, single-node
SQLite — are deliberate scope choices for a short build, and each has a clear,
low-risk upgrade path documented above and in `engineering-decisions.md`. The
performance figures are estimates, not benchmarks.

The three that would matter first in a real deployment are: **(1) auth + rate
limiting** (closes the cost-abuse hole), **(2) a task queue + Postgres** (unlocks
concurrency and resumability), and **(3) per-node tests** (makes the workflow
safe to change) — in that order.
