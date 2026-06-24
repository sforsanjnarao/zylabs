import type {
  ChatMessage,
  CreateSessionInput,
  Report,
  SessionDetail,
  SessionSummary,
} from "./types";

const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE ?? "http://127.0.0.1:8000";

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail ?? detail;
    } catch {
      // ignore
    }
    throw new Error(detail);
  }
  return res.json() as Promise<T>;
}

export const api = {
  listSessions: () => request<SessionSummary[]>("/api/sessions"),
  getSession: (id: string) => request<SessionDetail>(`/api/sessions/${id}`),
  createSession: (data: CreateSessionInput) =>
    request<SessionSummary>("/api/sessions", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  runWorkflow: (id: string) =>
    request<{ status: string }>(`/api/sessions/${id}/run`, { method: "POST" }),
  getReport: (id: string) => request<Report>(`/api/sessions/${id}/report`),
  getChat: (id: string) => request<ChatMessage[]>(`/api/sessions/${id}/chat`),
  sendChat: (id: string, message: string) =>
    request<ChatMessage>(`/api/sessions/${id}/chat`, {
      method: "POST",
      body: JSON.stringify({ message }),
    }),
  streamUrl: (id: string) => `${API_BASE}/api/sessions/${id}/stream`,
};
