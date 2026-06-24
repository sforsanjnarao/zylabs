"""Seed the database with a few realistic, completed research sessions.

Run from the backend folder:

    ./venv/bin/python seed.py

It is idempotent: companies that already exist (by name) are skipped, so you
can run it repeatedly without creating duplicates.
"""

import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

from dotenv import dotenv_values

# Load DATABASE_URL the same way the app does (last value in .env wins), and
# normalize the scheme BEFORE importing the app so the engine is built correctly.
_vals = dotenv_values(Path(__file__).parent / ".env")
_url = _vals.get("DATABASE_URL") or "sqlite:///./project01.db"
if _url.startswith("postgres://"):
    _url = "postgresql://" + _url[len("postgres://") :]
# Prefer psycopg v3 if installed (works around a broken local psycopg2/libpq);
# on Render psycopg v3 is absent, so we fall back to the default psycopg2.
try:
    import psycopg  # noqa: F401

    if _url.startswith("postgresql://"):
        _url = "postgresql+psycopg://" + _url[len("postgresql://") :]
except ImportError:
    pass
os.environ["DATABASE_URL"] = _url

from app.core.database import Base, SessionLocal, engine  # noqa: E402
from app.models.db_models import (  # noqa: E402
    ChatMessage,
    Report,
    ResearchSession,
    WorkflowStep,
)

STEPS = [
    ("planner", "Planned research questions and search strategy."),
    ("research", "Gathered and deduplicated web sources via Tavily."),
    ("analysis", "Synthesized findings into structured report sections."),
    ("quality_check", "Verified all required sections are complete."),
    ("report_generation", "Assembled the final sales briefing."),
]


def _report(**kwargs) -> Report:
    return Report(**kwargs)


SEED = [
    {
        "company_name": "Stripe",
        "website": "https://stripe.com",
        "objective": "Sell them an AI-powered fraud-analytics add-on",
        "report": {
            "overview": (
                "Stripe is a global payments infrastructure company powering "
                "online businesses of every size, from startups to large "
                "enterprises. It offers APIs for payments, billing, and "
                "financial services across 40+ countries."
            ),
            "products": (
                "Core: Payments, Billing, Connect, Radar (fraud), Terminal, "
                "Issuing, and the recently expanded Stripe Tax and Data Pipeline "
                "products."
            ),
            "customers": (
                "Amazon, Shopify, Salesforce, Marriott, plus millions of SMBs "
                "and high-growth startups. Strong developer-led adoption."
            ),
            "signals": (
                "Expanding into AI/ML for payment optimization; growing "
                "enterprise motion; recent push into stablecoin and global "
                "money movement."
            ),
            "risks": (
                "Intense competition (Adyen, Braintree); regulatory scrutiny in "
                "multiple regions; margin pressure at enterprise scale."
            ),
            "questions": [
                "What is the current fraud-detection false-positive rate vs. Radar?",
                "Which verticals see the highest chargeback volume?",
                "Is the data team open to third-party ML enrichment?",
            ],
            "outreach": (
                "Lead with chargeback-reduction ROI. Reference Radar's gaps for "
                "long-tail fraud patterns and offer a 30-day shadow-mode trial "
                "on historical transactions."
            ),
            "unknowns": [
                "Internal headcount on the risk/fraud team.",
                "Current annual fraud-loss budget.",
            ],
            "sources": [
                {"title": "Stripe — Official site", "url": "https://stripe.com"},
                {"title": "Stripe Newsroom", "url": "https://stripe.com/newsroom"},
            ],
        },
        "chat": [
            ("user", "What's the best angle to open with?"),
            (
                "assistant",
                "Lead with measurable chargeback-reduction ROI and offer a "
                "30-day shadow-mode trial on their historical transactions — it "
                "de-risks the evaluation and complements Radar rather than "
                "replacing it.",
            ),
        ],
    },
    {
        "company_name": "Notion",
        "website": "https://notion.so",
        "objective": "Pitch a workflow-automation integration",
        "report": {
            "overview": (
                "Notion is an all-in-one workspace combining notes, docs, "
                "wikis, and databases, popular with startups and increasingly "
                "with enterprises adopting Notion AI."
            ),
            "products": (
                "Notion workspace, Notion AI, Calendar (ex-Cron), and a growing "
                "API/integration ecosystem."
            ),
            "customers": (
                "Figma, Pixar, Headspace, and a massive long tail of startups "
                "and prosumers."
            ),
            "signals": (
                "Heavy investment in AI features; expanding enterprise admin "
                "and security controls; active developer/template community."
            ),
            "risks": (
                "Crowded productivity market (Coda, ClickUp, Microsoft Loop); "
                "performance at very large workspaces; AI cost pressure."
            ),
            "questions": [
                "How mature is their public API rate-limit tier for partners?",
                "What automation gaps do enterprise admins report?",
            ],
            "outreach": (
                "Position the integration as removing manual copy-paste between "
                "Notion and the customer's stack; quantify hours saved per team."
            ),
            "unknowns": [
                "Partner-program commercial terms.",
                "Roadmap for native automations.",
            ],
            "sources": [
                {"title": "Notion — Official site", "url": "https://notion.so"},
                {"title": "Notion API docs", "url": "https://developers.notion.com"},
            ],
        },
        "chat": [],
    },
    {
        "company_name": "Figma",
        "website": "https://figma.com",
        "objective": "Explore a design-ops consulting partnership",
        "report": {
            "overview": (
                "Figma is a collaborative interface-design platform used by "
                "product and design teams worldwide, expanding into whiteboarding "
                "(FigJam) and developer handoff (Dev Mode)."
            ),
            "products": (
                "Figma Design, FigJam, Dev Mode, and Figma Slides; growing AI "
                "assisted design features."
            ),
            "customers": (
                "Google, Microsoft, Airbnb, Uber — strong enterprise design-team "
                "penetration."
            ),
            "signals": (
                "Post-Adobe-deal independence; renewed product velocity; "
                "expansion beyond design into broader product workflows."
            ),
            "risks": (
                "Competition from Adobe XD legacy users and emerging AI design "
                "tools; enterprise procurement cycles."
            ),
            "questions": [
                "Which teams own design-system governance internally?",
                "Is there budget for external design-ops enablement?",
            ],
            "outreach": (
                "Offer a design-system audit + enablement program; tie outcomes "
                "to faster handoff and fewer design-to-code defects."
            ),
            "unknowns": [
                "Size of internal design-ops function.",
                "Preferred procurement vehicle for services.",
            ],
            "sources": [
                {"title": "Figma — Official site", "url": "https://figma.com"},
                {"title": "Figma Blog", "url": "https://figma.com/blog"},
            ],
        },
        "chat": [],
    },
    {
        "company_name": "Vercel",
        "website": "https://vercel.com",
        "objective": "Sell them an observability/monitoring layer",
        "report": {
            "overview": (
                "Vercel is the frontend cloud behind Next.js, providing hosting, "
                "edge functions, and developer tooling for modern web apps."
            ),
            "products": (
                "Vercel platform (deploys, edge, functions), Next.js, v0 (AI UI "
                "generation), and Vercel Observability features."
            ),
            "customers": (
                "Under Armour, Washington Post, Notion, and a large base of "
                "startups deploying Next.js apps."
            ),
            "signals": (
                "Aggressive AI tooling push (v0); growing enterprise edge "
                "adoption; expanding observability and analytics surface."
            ),
            "risks": (
                "Competition from Netlify, Cloudflare, and AWS Amplify; pricing "
                "sensitivity among high-traffic customers."
            ),
            "questions": [
                "What gaps exist between native Analytics and full APM?",
                "How do enterprise customers handle cross-service tracing today?",
            ],
            "outreach": (
                "Complement native Vercel Analytics with deep distributed "
                "tracing across their backend services; offer a free traffic "
                "replay on a staging project."
            ),
            "unknowns": [
                "Current monitoring vendor spend.",
                "Internal SRE/observability team size.",
            ],
            "sources": [
                {"title": "Vercel — Official site", "url": "https://vercel.com"},
                {"title": "Vercel Changelog", "url": "https://vercel.com/changelog"},
            ],
        },
        "chat": [],
    },
]


def main() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    created = 0
    try:
        now = datetime.now(timezone.utc)
        for i, item in enumerate(SEED):
            exists = (
                db.query(ResearchSession)
                .filter(ResearchSession.company_name == item["company_name"])
                .first()
            )
            if exists:
                print(f"skip (exists): {item['company_name']}")
                continue

            # Stagger created_at so history ordering looks natural.
            ts = now - timedelta(hours=i, minutes=i * 7)
            session = ResearchSession(
                company_name=item["company_name"],
                website=item["website"],
                objective=item["objective"],
                status="completed",
                created_at=ts,
                updated_at=ts,
            )
            session.report = Report(**item["report"])
            for j, (name, detail) in enumerate(STEPS):
                session.steps.append(
                    WorkflowStep(
                        step_name=name,
                        status="done",
                        output={"name": name, "status": "done", "detail": detail},
                        created_at=ts + timedelta(seconds=j * 3),
                    )
                )
            for k, (role, content) in enumerate(item["chat"]):
                session.messages.append(
                    ChatMessage(
                        role=role,
                        content=content,
                        created_at=ts + timedelta(minutes=2, seconds=k * 5),
                    )
                )
            db.add(session)
            created += 1
            print(f"seeded: {item['company_name']}")

        db.commit()
        print(f"\nDone. Created {created} new session(s).")
    finally:
        db.close()


if __name__ == "__main__":
    main()
