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
 *
 * C2 review: the count hint was dropped from the breadcrumb
 * scope because the /prospects/{id} endpoint doesn't return
 * a run-level total. The count is visible on the
 * /scout-runs/:id/results page (Layer 2) instead.
 */

import { useNavigate } from "react-router-dom";
import { MapPin, ArrowRight } from "lucide-react";

import { useT } from "@/i18n";
import { cn } from "@/lib/utils";

interface Props {
  scoutRunId: string | null | undefined;
  className?: string;
}

export function ScoutRunBreadcrumb({ scoutRunId, className }: Props) {
  const t = useT();
  const navigate = useNavigate();

  if (!scoutRunId) return null;

  // Show first 8 chars of the UUID for a friendly display
  const shortId = scoutRunId.slice(0, 8);

  // M11: single button (was: text-button + separate "view" button).
  // M8: wrap in <nav> for the breadcrumb landmark.
  return (
    <nav
      aria-label="breadcrumb"
      className={cn(
        "flex items-center gap-2 text-sm text-muted-foreground px-3 py-2 rounded-md",
        "bg-muted/40 border border-border/50",
        className,
      )}
    >
      <MapPin className="h-4 w-4 shrink-0" aria-hidden="true" />
      <button
        type="button"
        onClick={() => navigate(`/scout-runs/${scoutRunId}/results`)}
        className="flex items-center gap-1 font-medium text-foreground hover:underline focus:outline-none focus:ring-2 focus:ring-ring rounded-sm"
      >
        <span>
          {t.scoutRun.breadcrumb.foundFrom}{" "}
          {t.scoutRun.breadcrumb.runLabel.replace("{id}", shortId)}
        </span>
        <ArrowRight className="h-3 w-3" aria-hidden="true" />
        <span className="sr-only">{t.scoutRun.breadcrumb.view}</span>
      </button>
    </nav>
  );
}
