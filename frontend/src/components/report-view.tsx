import type { Report, Source } from "@/lib/types";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Markdown } from "@/components/markdown";

/**
 * Turn [n] citation markers into markdown links pointing at the matching
 * numbered source, so they render as clickable superscript references.
 */
function linkCitations(text: string, sources: Source[]): string {
  const byNumber = new Map<number, Source>();
  sources.forEach((s, i) => byNumber.set(s.n ?? i + 1, s));
  return text.replace(/\[(\d+)\]/g, (whole, num) => {
    const src = byNumber.get(Number(num));
    return src ? `[[${num}]](${src.url})` : whole;
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
      <Markdown>{linkCitations(text, sources)}</Markdown>
    </div>
  );
}

function ListSection({
  title,
  items,
  sources,
}: {
  title: string;
  items: string[];
  sources: Source[];
}) {
  if (!items || items.length === 0) return null;
  return (
    <div className="space-y-1">
      <h3 className="text-xs font-semibold uppercase tracking-wide text-primary">
        {title}
      </h3>
      <ul className="list-disc space-y-1 pl-5 text-sm">
        {items.map((it, i) => (
          <li key={i}>
            <Markdown className="inline">{linkCitations(it, sources)}</Markdown>
          </li>
        ))}
      </ul>
    </div>
  );
}

export function ReportView({ report }: { report: Report }) {
  const sources = report.sources;
  return (
    <Card>
      <CardHeader>
        <CardTitle>Research report</CardTitle>
      </CardHeader>
      <CardContent className="space-y-5">
        <TextSection
          title="Company Overview"
          text={report.overview}
          sources={sources}
        />
        <TextSection
          title="Products & Services"
          text={report.products}
          sources={sources}
        />
        <TextSection
          title="Target Customers"
          text={report.customers}
          sources={sources}
        />
        <TextSection
          title="Business Signals"
          text={report.signals}
          sources={sources}
        />
        <TextSection
          title="Risks & Challenges"
          text={report.risks}
          sources={sources}
        />
        <ListSection
          title="Suggested Discovery Questions"
          items={report.questions}
          sources={sources}
        />
        <TextSection
          title="Suggested Outreach Strategy"
          text={report.outreach}
          sources={sources}
        />
        <ListSection title="Unknowns" items={report.unknowns} sources={sources} />
        {sources.length > 0 && (
          <div className="space-y-1">
            <h3 className="text-xs font-semibold uppercase tracking-wide text-primary">
              Sources
            </h3>
            <ul className="space-y-1 text-sm">
              {sources.map((s, i) => (
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
