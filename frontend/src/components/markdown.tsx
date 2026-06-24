import ReactMarkdown, { type Components } from "react-markdown";
import remarkGfm from "remark-gfm";
import { cn } from "@/lib/utils";

/**
 * Render an anchor. Citation links (text like "[3]") are shown as a small
 * superscript marker; everything else renders as a normal inline link.
 */
function isCitation(children: React.ReactNode): boolean {
  return (
    typeof children === "string" && /^\[\d+\]$/.test(children.trim())
  );
}

const components: Components = {
  p: ({ children }) => (
    <p className="text-sm leading-relaxed [&:not(:first-child)]:mt-2">
      {children}
    </p>
  ),
  ul: ({ children }) => (
    <ul className="my-2 list-disc space-y-1 pl-5 text-sm">{children}</ul>
  ),
  ol: ({ children }) => (
    <ol className="my-2 list-decimal space-y-1 pl-5 text-sm">{children}</ol>
  ),
  li: ({ children }) => <li className="leading-relaxed">{children}</li>,
  strong: ({ children }) => (
    <strong className="font-semibold">{children}</strong>
  ),
  em: ({ children }) => <em className="italic">{children}</em>,
  h1: ({ children }) => (
    <h3 className="mt-3 text-sm font-semibold">{children}</h3>
  ),
  h2: ({ children }) => (
    <h3 className="mt-3 text-sm font-semibold">{children}</h3>
  ),
  h3: ({ children }) => (
    <h3 className="mt-3 text-sm font-semibold">{children}</h3>
  ),
  code: ({ children }) => (
    <code className="rounded bg-muted px-1 py-0.5 text-xs">{children}</code>
  ),
  a: ({ children, href }) => {
    const cite = isCitation(children);
    const link = (
      <a
        href={href}
        target="_blank"
        rel="noreferrer"
        className="text-primary underline-offset-2 hover:underline"
      >
        {children}
      </a>
    );
    return cite ? <sup className="ml-0.5">{link}</sup> : link;
  },
};

export function Markdown({
  children,
  className,
}: {
  children: string;
  className?: string;
}) {
  return (
    <div className={cn("text-sm leading-relaxed", className)}>
      <ReactMarkdown remarkPlugins={[remarkGfm]} components={components}>
        {children}
      </ReactMarkdown>
    </div>
  );
}
