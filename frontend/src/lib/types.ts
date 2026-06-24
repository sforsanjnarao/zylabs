// Types mirroring the FastAPI backend schemas.

export type SessionStatus = "pending" | "running" | "completed" | "failed";

export interface SessionSummary {
  id: string;
  company_name: string;
  website: string;
  objective: string;
  status: SessionStatus;
  created_at: string;
}

export interface Source {
  title: string;
  url: string;
  n?: number;
  facet?: string;
  date?: string;
}

export interface Report {
  overview: string;
  products: string;
  customers: string;
  signals: string;
  risks: string;
  questions: string[];
  outreach: string;
  unknowns: string[];
  sources: Source[];
}

export interface WorkflowStep {
  step_name: string;
  status: "running" | "done" | "failed";
  output: { name?: string; status?: string; detail?: string } & Record<string, unknown>;
  created_at: string;
}

export interface SessionDetail extends SessionSummary {
  error: string;
  report: Report | null;
  steps: WorkflowStep[];
}

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  created_at: string;
}

export interface CreateSessionInput {
  company_name: string;
  website?: string;
  objective?: string;
}

// Shape of an SSE "step" event payload.
export interface StepEvent {
  name: string;
  status: "running" | "done" | "failed";
  output: { detail?: string } & Record<string, unknown>;
}

export interface DoneEvent {
  status: SessionStatus;
  error: string;
}
