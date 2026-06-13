import { Badge } from "./badge";
import type { ProspectStatus, ProspectGrade } from "@/types";

/**
 * StatusPill — semantic status indicator for prospect pipeline.
 * Maps status to a colored badge variant.
 */

const statusVariant: Record<ProspectStatus, string> = {
  new: "status-new",
  enriching: "status-enriching",
  scored: "status-scored",
  approved: "default",
  contacted: "status-contacted",
  replied: "status-replied",
  won: "status-won",
  lost: "status-lost",
  archived: "muted",
};

const statusLabel: Record<ProspectStatus, string> = {
  new: "New",
  enriching: "Enriching",
  scored: "Scored",
  approved: "Approved",
  contacted: "Contacted",
  replied: "Replied",
  won: "Won",
  lost: "Lost",
  archived: "Archived",
};

export function StatusPill({ status }: { status: ProspectStatus }) {
  return (
    <Badge variant={statusVariant[status] as any}>
      {statusLabel[status]}
    </Badge>
  );
}

const gradeVariant: Record<ProspectGrade, string> = {
  A: "grade-a",
  B: "grade-b",
  C: "grade-c",
  D: "grade-d",
};

export function GradePill({ grade }: { grade: ProspectGrade }) {
  return (
    <Badge variant={gradeVariant[grade] as any} className="font-bold">
      {grade}
    </Badge>
  );
}
