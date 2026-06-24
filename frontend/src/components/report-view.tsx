import type { Report } from "@/lib/types";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

function TextSection({ title, text }: { title: string; text: string }) {
  if (!text) return null;
  return (
    <div className="space-y-1">
      <h3 className="text-xs font-semibold uppercase tracking-wide text-primary">
        {title}
      </h3>
      <p className="text-sm leading-relaxed">{text}</p>
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
        <TextSection title="Company Overview" text={report.overview} />
        <TextSection title="Products & Services" text={report.products} />
        <TextSection title="Target Customers" text={report.customers} />
        <TextSection title="Business Signals" text={report.signals} />
        <TextSection title="Risks & Challenges" text={report.risks} />
        <ListSection
          title="Suggested Discovery Questions"
          items={report.questions}
        />
        <TextSection title="Suggested Outreach Strategy" text={report.outreach} />
        <ListSection title="Unknowns" items={report.unknowns} />
        {report.sources.length > 0 && (
          <div className="space-y-1">
            <h3 className="text-xs font-semibold uppercase tracking-wide text-primary">
              Sources
            </h3>
            <ul className="list-disc space-y-1 pl-5 text-sm">
              {report.sources.map((s, i) => (
                <li key={i} className="break-all">
                  <a
                    href={s.url}
                    target="_blank"
                    rel="noreferrer"
                    className="text-primary underline-offset-2 hover:underline"
                  >
                    {s.title || s.url}
                  </a>
                </li>
              ))}
            </ul>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
