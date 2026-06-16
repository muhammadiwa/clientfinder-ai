/**
 * ScoutRunBreadcrumb (Sprint 4 PR 3).
 *
 * Small 1-line breadcrumb shown on ProspectDetail when the
 * prospect was discovered by a ScoutRun. Implements the
 * "Link, don't load" pattern from the redesign — shows
 * provenance with a link, doesn't dump the source data inline.
 *
 * Null-safe: if the prospect has no scout_run_id (legacy /
 * manual import), returns null.
 */

import { useNavigate } from "react-router-dom";
import { MapPin, ArrowRight } from "lucide-react";

import { useT } from "@/i18n";
import { cn } from "@/lib/utils";

interface Props {
  scoutRunId: string | null | undefined;
  totalCount?: number | null;
  className?: string;
}

export function ScoutRunBreadcrumb({ scoutRunId, totalCount, className }: Props) {
  const t = useT();
  const navigate = useNavigate();

  if (!scoutRunId) return null;

  // Show first 8 chars of the UUID for a friendly display
  const shortId = scoutRunId.slice(0, 8);

  return (
    <div
      className={cn(
        "flex items-center gap-2 text-sm text-muted-foreground px-3 py-2 rounded-md",
        "bg-muted/40 border border-border/50",
        className,
      )}
    >
      <MapPin className="h-4 w-4 shrink-0" />
      <span>
        {t.scoutRun.breadcrumb.foundFrom}{" "}
        <button
          onClick={() => navigate(`/scout-runs/${scoutRunId}/results`)}
          className="font-medium text-foreground hover:underline"
        >
          {t.scoutRun.breadcrumb.runLabel.replace("{id}", shortId)}
        </button>
        {typeof totalCount === "number" && totalCount > 0 && (
          <span className="ml-1 text-xs">
            · {totalCount} {t.scoutRun.breadcrumb.resultsCount}
          </span>
        )}
      </span>
      <button
        onClick={() => navigate(`/scout-runs/${scoutRunId}/results`)}
        className="ml-auto flex items-center gap-1 text-xs text-primary hover:underline"
      >
        {t.scoutRun.breadcrumb.view}
        <ArrowRight className="h-3 w-3" />
      </button>
    </div>
  );
}
