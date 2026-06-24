import type { WorkflowStep } from "@/lib/types";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { cn } from "@/lib/utils";

const STEP_LABELS: Record<string, string> = {
  planner: "Planning research",
  research: "Searching the web",
  analysis: "Analyzing findings",
  quality_check: "Quality check",
  report_gen: "Generating report",
};

interface Props {
  steps: WorkflowStep[];
  running: boolean;
}

export function WorkflowProgress({ steps, running }: Props) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Workflow progress</CardTitle>
      </CardHeader>
      <CardContent>
        <ol className="space-y-0">
          {steps.map((s, i) => {
            const label = STEP_LABELS[s.step_name] ?? s.step_name;
            const detail = s.output?.detail;
            return (
              <li
                key={i}
                className="flex items-center gap-3 border-b py-2.5 last:border-b-0"
              >
                <span
                  className={cn(
                    "h-2.5 w-2.5 shrink-0 rounded-full",
                    s.status === "failed"
                      ? "bg-red-500"
                      : s.status === "running"
                        ? "bg-amber-500"
                        : "bg-green-500"
                  )}
                />
                <span className="flex-1 text-sm">
                  {label}
                  {detail ? (
                    <span className="text-muted-foreground"> — {detail}</span>
                  ) : null}
                </span>
                <span className="text-xs uppercase text-muted-foreground">
                  {s.status}
                </span>
              </li>
            );
          })}
          {running && (
            <li className="flex items-center gap-3 py-2.5">
              <span className="h-2.5 w-2.5 shrink-0 animate-pulse rounded-full bg-amber-500" />
              <span className="flex-1 text-sm text-muted-foreground">
                Working…
              </span>
            </li>
          )}
          {steps.length === 0 && !running && (
            <p className="text-sm text-muted-foreground">No steps recorded.</p>
          )}
        </ol>
      </CardContent>
    </Card>
  );
}
