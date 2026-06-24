import { Badge } from "@/components/ui/badge";
import type { SessionStatus } from "@/lib/types";
import { cn } from "@/lib/utils";

const STYLES: Record<SessionStatus, string> = {
  completed: "bg-green-100 text-green-700 border-green-200",
  running: "bg-amber-100 text-amber-700 border-amber-200",
  pending: "bg-amber-100 text-amber-700 border-amber-200",
  failed: "bg-red-100 text-red-700 border-red-200",
};

export function StatusBadge({ status }: { status: SessionStatus }) {
  return (
    <Badge variant="outline" className={cn("capitalize", STYLES[status])}>
      {status}
    </Badge>
  );
}
