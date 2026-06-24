"""API request/response schemas (Pydantic models).

These define the JSON shapes the API accepts and returns. Keeping them
separate from the database models is a common, clean practice.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


# ---------- Sessions ----------
class SessionCreate(BaseModel):
    """Body for POST /api/sessions."""
    company_name: str = Field(min_length=1, description="Company to research (required)")
    website: str = ""
    objective: str = ""

    @field_validator("company_name")
    @classmethod
    def _not_blank(cls, v: str) -> str:
        """Reject whitespace-only names that slip past min_length."""
        v = v.strip()
        if not v:
            raise ValueError("company_name must not be empty")
        return v


class SessionSummary(BaseModel):
    """Compact session info for the history list."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    company_name: str
    website: str
    objective: str
    status: str
    created_at: datetime


# ---------- Report ----------
class ReportOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    overview: str
    products: str
    customers: str
    signals: str
    risks: str
    questions: list
    outreach: str
    unknowns: list
    sources: list


# ---------- Workflow steps ----------
class StepOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    step_name: str
    status: str
    output: dict
    created_at: datetime


# ---------- Full session detail ----------
class SessionDetail(SessionSummary):
    error: str = ""
    report: ReportOut | None = None
    steps: list[StepOut] = []


# ---------- Chat ----------
class ChatRequest(BaseModel):
    message: str


class ChatMessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    role: str
    content: str
    created_at: datetime
