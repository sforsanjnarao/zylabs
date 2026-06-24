# zylabs AI Research Copilot

An AI-powered research copilot that helps you prepare for a sales or business
meeting. Give it a company name, website, and your objective, and it runs a
multi-step **LangGraph** workflow that researches the company on the live web
and produces a structured sales briefing — then lets you chat with the report.

> "Your sellers run the conversation. We do everything else."

---

## Features

- **Create research sessions** with a company, website, and objective.
- **Multi-node LangGraph workflow** (Planner → Research → Analysis → Quality Check → Report) with a conditional quality-retry loop.
- **Live web research** via Tavily, with real source URLs.
- **Structured report** covering 9 sections: Company Overview, Products & Services, Target Customers, Business Signals, Risks & Challenges, Discovery Questions, Outreach Strategy, Unknowns, and Sources.
- **Live progress** streamed to the UI via Server-Sent Events.
- **Follow-up chat** grounded in the generated report.
- **Persistence** of sessions, reports, steps, and chat history (SQLite).

---

## Tech Stack

| Layer       | Technology                                          |
| ----------- | --------------------------------------------------- |
| Frontend    | React (Next.js App Router) + TypeScript + Tailwind + shadcn/ui |
| Backend     | Python + FastAPI                                    |
| AI Workflow | LangGraph + LangChain                               |
| LLM         | OpenAI (`gpt-4o-mini` by default)                  |
| Web Search  | Tavily                                              |
| Storage     | SQLite (via SQLAlchemy)                             |

---

## Project Structure

```
zylabs/
├── backend/
│   ├── app/
│   │   ├── api/            # FastAPI routes (sessions, workflow, chat)
│   │   ├── workflow/       # LangGraph graph, nodes, LLM + search helpers
│   │   ├── models/         # SQLAlchemy entities
│   │   ├── services/       # workflow runner + chat logic
│   │   ├── core/           # config + database
│   │   ├── schemas.py      # Pydantic request/response models
│   │   └── main.py         # app entry point
│   ├── requirements.txt
│   └── .env.example
├── frontend/               # Next.js app (TypeScript + Tailwind + shadcn/ui)
│   ├── src/
│   │   ├── app/            # routes: / (home) and /sessions/[id]
│   │   ├── components/     # UI components (report, progress, chat) + ui/
│   │   └── lib/            # typed API client + shared types
│   └── .env.example
├── docs/
│   ├── architecture.md
│   ├── product-improvements.md
│   ├── engineering-decisions.md
│   └── non-functional-requirements.md
└── README.md
```

---

## Getting Started

### Prerequisites

- Python 3.11+
- Node.js 18+
- An OpenAI API key and a Tavily API key

### 1. Backend

```bash
cd backend
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env              # then edit .env and add your keys
```

Edit `backend/.env`:

```
OPENAI_API_KEY=sk-...
TAVILY_API_KEY=tvly-...
```

Run the server:

```bash
uvicorn app.main:app --reload
```

The API runs at `http://127.0.0.1:8000` (interactive docs at `/docs`).

### 2. Frontend

In a second terminal:

```bash
cd frontend
npm install
cp .env.example .env.local        # points the app at the backend
npm run dev
```

Open `http://localhost:3000`.

`.env.local` sets `NEXT_PUBLIC_API_BASE` (defaults to `http://127.0.0.1:8000`).

---

## How It Works (quick tour)

1. You create a session and press **Start research**.
2. The backend launches the LangGraph workflow in a background thread.
3. Each node (planner, research, analysis, quality check, report) runs in turn,
   writing progress to the database.
4. The frontend streams that progress live via SSE.
5. When finished, the structured report is displayed and you can chat with it.

## Documentation

- [`docs/architecture.md`](docs/architecture.md) — layers, data flow, tradeoffs.
- [`docs/engineering-decisions.md`](docs/engineering-decisions.md) — key decisions, alternatives, tradeoffs.
- [`docs/product-improvements.md`](docs/product-improvements.md) — weaknesses, top-3 next, business thinking.
- [`docs/non-functional-requirements.md`](docs/non-functional-requirements.md) — performance, scalability, reliability, security, observability targets (current vs. production).

---

## Configuration

All settings are read from `backend/.env` (see `.env.example`):

| Variable          | Default                  | Description                |
| ----------------- | ------------------------ | -------------------------- |
| `OPENAI_API_KEY`  | —                        | OpenAI key (required)      |
| `TAVILY_API_KEY`  | —                        | Tavily key (required)      |
| `OPENAI_MODEL`    | `gpt-4o-mini`            | Chat model                 |
| `DATABASE_URL`    | `sqlite:///./zylabs.db`  | Database connection string |
| `LOG_LEVEL`       | `INFO`                   | Logging verbosity          |
| `CORS_ORIGINS`    | `http://localhost:3000,http://127.0.0.1:3000` | Comma-separated allowed frontend origins |

---

## Deployment

The app deploys as two services plus a managed database:

- **Frontend → Vercel** (Next.js)
- **Backend → Render** (FastAPI, via `render.yaml`)
- **Database → Neon** (managed Postgres)

### 1. Database (Neon)
Create a free project at [neon.tech](https://neon.tech) and copy the connection
string (looks like `postgresql://user:pass@host/db?sslmode=require`).

### 2. Backend (Render)
1. Render Dashboard → **New → Blueprint** → select this repo (it reads
   `render.yaml`).
2. Set the secret env vars in the dashboard:
   - `OPENAI_API_KEY`, `TAVILY_API_KEY`
   - `DATABASE_URL` → the Neon connection string
   - `CORS_ORIGINS` → your Vercel URL (add after step 3)
3. Deploy and note the backend URL, e.g. `https://zylabs-backend.onrender.com`.

> The backend supports both SQLite (local) and Postgres (production)
> automatically based on `DATABASE_URL`.

### 3. Frontend (Vercel)
1. [vercel.com](https://vercel.com) → **Add New → Project** → import this repo.
2. Set **Root Directory** to `frontend`.
3. Add env var `NEXT_PUBLIC_API_BASE` → your Render backend URL.
4. Deploy, then add the resulting Vercel URL to the backend's `CORS_ORIGINS`
   and redeploy the backend.

> Note: Render's free backend sleeps when idle, so the first request after a
> period of inactivity can take ~50s to wake.
