"use client";

import { useEffect, useRef, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { api } from "@/lib/api";
import type {
  DoneEvent,
  Report,
  SessionDetail,
  SessionStatus,
  StepEvent,
  WorkflowStep,
} from "@/lib/types";
import { StatusBadge } from "@/components/status-badge";
import { WorkflowProgress } from "@/components/workflow-progress";
import { ReportView } from "@/components/report-view";
import { ChatPanel } from "@/components/chat-panel";

function stepFromEvent(e: StepEvent): WorkflowStep {
  return {
    step_name: e.name,
    status: e.status,
    output: e.output ?? {},
    created_at: new Date().toISOString(),
  };
}

export default function SessionPage() {
  const { id } = useParams<{ id: string }>();
  const [session, setSession] = useState<SessionDetail | null>(null);
  const [report, setReport] = useState<Report | null>(null);
  const [steps, setSteps] = useState<WorkflowStep[]>([]);
  const [status, setStatus] = useState<SessionStatus>("pending");
  const [error, setError] = useState("");
  const esRef = useRef<EventSource | null>(null);

  useEffect(() => {
    if (!id) return;
    let cancelled = false;

    function startStream() {
      setSteps([]);
      const es = new EventSource(api.streamUrl(id));
      esRef.current = es;

      es.addEventListener("step", (e) => {
        const data = JSON.parse((e as MessageEvent).data) as StepEvent;
        setSteps((prev) => [...prev, stepFromEvent(data)]);
      });
      es.addEventListener("done", (e) => {
        const data = JSON.parse((e as MessageEvent).data) as DoneEvent;
        setStatus(data.status);
        if (data.status === "completed") {
          api.getReport(id).then(setReport).catch(() => {});
        } else if (data.status === "failed") {
          setError(data.error || "Workflow failed");
        }
        es.close();
      });
      es.onerror = () => es.close();
    }

    (async () => {
      try {
        const s = await api.getSession(id);
        if (cancelled) return;
        setSession(s);
        setStatus(s.status);
        if (s.status === "completed") {
          setSteps(s.steps);
          setReport(s.report);
        } else if (s.status === "failed") {
          setSteps(s.steps);
          setError(s.error || "Workflow failed");
        } else {
          startStream();
        }
      } catch (e) {
        if (!cancelled) setError((e as Error).message);
      }
    })();

    return () => {
      cancelled = true;
      esRef.current?.close();
    };
  }, [id]);

  const running = status === "pending" || status === "running";

  return (
    <div className="space-y-6">
      <Link
        href="/"
        className="text-sm text-muted-foreground hover:text-foreground"
      >
        ← All sessions
      </Link>

      {session && (
        <div className="space-y-2">
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold tracking-tight">
              {session.company_name}
            </h1>
            <StatusBadge status={status} />
          </div>
          {session.website && (
            <a
              href={session.website}
              target="_blank"
              rel="noreferrer"
              className="text-sm text-muted-foreground hover:underline"
            >
              {session.website}
            </a>
          )}
          {session.objective && (
            <p className="text-sm text-foreground/80">{session.objective}</p>
          )}
        </div>
      )}

      <WorkflowProgress steps={steps} running={running} />

      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      )}

      {report && <ReportView report={report} />}

      {status === "completed" && <ChatPanel sessionId={id} />}
    </div>
  );
}
