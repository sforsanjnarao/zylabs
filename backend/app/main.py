"""FastAPI application entry point."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import chat, sessions, workflow
from app.core.config import settings
from app.core.database import Base, engine

# Import models so their tables register on Base before we create them.
from app.models import db_models  # noqa: F401

# ---- Logging (bonus: observability) ----
logging.basicConfig(
    level=settings.log_level,
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
)
logger = logging.getLogger("project01")

# ---- Create database tables if they don't exist yet ----
Base.metadata.create_all(bind=engine)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Project01 backend started. Model=%s", settings.openai_model)
    yield
    logger.info("Project01 backend shutting down.")


# ---- The app ----
app = FastAPI(
    title="Project01 AI Research Copilot",
    version="0.1.0",
    lifespan=lifespan,
)

# Allow the React dev server to call this API.
app.add_middleware(
    CORSMiddleware,
    # Explicit origins (not "*"): a wildcard is invalid alongside
    # allow_credentials per the CORS spec. Configure via CORS_ORIGINS in .env.
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(sessions.router)
app.include_router(workflow.router)
app.include_router(chat.router)


@app.get("/health")
def health():
    return {"status": "ok"}
