"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { api } from "@/lib/api";
import type { SessionSummary } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { StatusBadge } from "@/components/status-badge";

export default function Home() {
  const router = useRouter();
  const [sessions, setSessions] = useState<SessionSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [form, setForm] = useState({
    company_name: "",
    website: "",
    objective: "",
  });

  useEffect(() => {
    api
      .listSessions()
      .then(setSessions)
      .catch((e: Error) => toast.error(e.message))
      .finally(() => setLoading(false));
  }, []);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!form.company_name.trim()) return;
    setSubmitting(true);
    try {
      const session = await api.createSession(form);
      await api.runWorkflow(session.id);
      router.push(`/sessions/${session.id}`);
    } catch (e) {
      toast.error((e as Error).message);
      setSubmitting(false);
    }
  }

  return (
    <div className="space-y-8">
      <section className="space-y-2">
        <h1 className="text-3xl font-bold tracking-tight">
          Research any company in seconds
        </h1>
        <p className="max-w-2xl text-muted-foreground">
          Create a research session and our AI workflow builds a structured sales
          briefing — overview, customers, risks, outreach strategy and more.
        </p>
      </section>

      <div className="grid gap-6 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>New research session</CardTitle>
            <CardDescription>
              Tell us who to research and why.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="company">Company name *</Label>
                <Input
                  id="company"
                  value={form.company_name}
                  onChange={(e) =>
                    setForm({ ...form, company_name: e.target.value })
                  }
                  placeholder="e.g. Stripe"
                  required
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="website">Website</Label>
                <Input
                  id="website"
                  value={form.website}
                  onChange={(e) =>
                    setForm({ ...form, website: e.target.value })
                  }
                  placeholder="https://stripe.com"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="objective">Research objective</Label>
                <Textarea
                  id="objective"
                  value={form.objective}
                  onChange={(e) =>
                    setForm({ ...form, objective: e.target.value })
                  }
                  placeholder="e.g. I want to sell them a fraud-detection tool"
                  rows={3}
                />
              </div>
              <Button type="submit" disabled={submitting} className="w-full">
                {submitting ? "Starting…" : "Start research"}
              </Button>
            </form>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Session history</CardTitle>
            <CardDescription>Your past research sessions.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {loading && (
              <>
                <Skeleton className="h-14 w-full" />
                <Skeleton className="h-14 w-full" />
              </>
            )}
            {!loading && sessions.length === 0 && (
              <p className="text-sm text-muted-foreground">
                No sessions yet. Create your first one!
              </p>
            )}
            {sessions.map((s) => (
              <button
                key={s.id}
                onClick={() => router.push(`/sessions/${s.id}`)}
                className="flex w-full items-center justify-between rounded-lg border p-3 text-left transition-colors hover:border-primary hover:bg-accent"
              >
                <div className="min-w-0">
                  <div className="truncate font-medium">{s.company_name}</div>
                  <div className="truncate text-xs text-muted-foreground">
                    {s.objective || "No objective"}
                  </div>
                </div>
                <StatusBadge status={s.status} />
              </button>
            ))}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
