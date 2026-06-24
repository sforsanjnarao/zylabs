# Project01 AI Research Copilot

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
project01/
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
│   └── engineering-decisions.md
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

See `docs/architecture.md` for the full design.

---

## Configuration

All settings are read from `backend/.env` (see `.env.example`):

| Variable          | Default                  | Description                |
| ----------------- | ------------------------ | -------------------------- |
| `OPENAI_API_KEY`  | —                        | OpenAI key (required)      |
| `TAVILY_API_KEY`  | —                        | Tavily key (required)      |
| `OPENAI_MODEL`    | `gpt-4o-mini`            | Chat model                 |
| `DATABASE_URL`    | `sqlite:///./project01.db`  | Database connection string |
| `LOG_LEVEL`       | `INFO`                   | Logging verbosity          |
