import type { Report, Source } from "@/lib/types";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import React from "react";

/**
 * Render text that may contain [n] citation markers, turning each marker into
 * a small superscript link to the matching numbered source.
 */
function withCitations(text: string, sources: Source[]): React.ReactNode[] {
  const byNumber = new Map<number, Source>();
  sources.forEach((s, i) => byNumber.set(s.n ?? i + 1, s));

  return text.split(/(\[\d+\])/g).map((part, i) => {
    const m = part.match(/^\[(\d+)\]$/);
    if (!m) return <React.Fragment key={i}>{part}</React.Fragment>;
    const n = Number(m[1]);
    const src = byNumber.get(n);
    if (!src) return <React.Fragment key={i}>{part}</React.Fragment>;
    return (
      <sup key={i} className="ml-0.5">
        <a
          href={src.url}
          target="_blank"
          rel="noreferrer"
          title={src.title || src.url}
          className="text-primary underline-offset-2 hover:underline"
        >
          [{n}]
        </a>
      </sup>
    );
  });
}

function TextSection({
  title,
  text,
  sources,
}: {
  title: string;
  text: string;
  sources: Source[];
}) {
  if (!text) return null;
  return (
    <div className="space-y-1">
      <h3 className="text-xs font-semibold uppercase tracking-wide text-primary">
        {title}
      </h3>
      <p className="text-sm leading-relaxed">{withCitations(text, sources)}</p>
    </div>
  );
}

function ListSection({ title, items }: { title: string; items: string[] }) {
  if (!items || items.length === 0) return null;
  return (
    <div className="space-y-1">
      <h3 className="text-xs font-semibold uppercase tracking-wide text-primary">
        {title}
      </h3>
      <ul className="list-disc space-y-1 pl-5 text-sm">
        {items.map((it, i) => (
          <li key={i}>{it}</li>
        ))}
      </ul>
    </div>
  );
}

export function ReportView({ report }: { report: Report }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Research report</CardTitle>
      </CardHeader>
      <CardContent className="space-y-5">
        <TextSection
          title="Company Overview"
          text={report.overview}
          sources={report.sources}
        />
        <TextSection
          title="Products & Services"
          text={report.products}
          sources={report.sources}
        />
        <TextSection
          title="Target Customers"
          text={report.customers}
          sources={report.sources}
        />
        <TextSection
          title="Business Signals"
          text={report.signals}
          sources={report.sources}
        />
        <TextSection
          title="Risks & Challenges"
          text={report.risks}
          sources={report.sources}
        />
        <ListSection
          title="Suggested Discovery Questions"
          items={report.questions}
        />
        <TextSection
          title="Suggested Outreach Strategy"
          text={report.outreach}
          sources={report.sources}
        />
        <ListSection title="Unknowns" items={report.unknowns} />
        {report.sources.length > 0 && (
          <div className="space-y-1">
            <h3 className="text-xs font-semibold uppercase tracking-wide text-primary">
              Sources
            </h3>
            <ul className="space-y-1 text-sm">
              {report.sources.map((s, i) => (
                <li key={i} className="break-all">
                  <span className="mr-1 text-muted-foreground">
                    [{s.n ?? i + 1}]
                  </span>
                  <a
                    href={s.url}
                    target="_blank"
                    rel="noreferrer"
                    className="text-primary underline-offset-2 hover:underline"
                  >
                    {s.title || s.url}
                  </a>
                  {s.date && (
                    <span className="ml-1 text-xs text-muted-foreground">
                      ({s.date})
                    </span>
                  )}
                </li>
              ))}
            </ul>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
