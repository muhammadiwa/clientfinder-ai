/**
 * ScoutRunResults — Layer 2 of the hybrid C display (Sprint 4 PR 3).
 *
 * Dedicated page at /scout-runs/:id/results showing the FULL raw
 * data from a ScoutRun. ProspectDetail (Layer 1) shows a 1-line
 * breadcrumb link to this page; the actual payload lives here.
 *
 * The page is paginated (25 per page default), sortable by the
 * raw_data fields (rating, review_count, hours), and deep-linkable.
 *
 * Code-review patches applied (PR 3 followup):
 * - I1: AbortController + cancelled flag to prevent stale-response
 *       races on rapid pagination.
 * - I2: URL.canParse() guard before new URL() (the old code
 *       crashed the row on a malformed website string).
 * - I4: rel="noopener noreferrer" (was just "noreferrer").
 * - I5: branch on data.total === 0 vs out-of-range page.
 * - M1: protocol validation (rejects mailto:/tel:/javascript:).
 * - M2: single "no results" message when total === 0.
 * - M3: array-coercion for legacy query.keywords.
 * - M4: redirect to /login if token is empty.
 * - M7: <tr> with role="button" + tabIndex + onKeyDown for a11y.
 */

import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import {
  ArrowLeft,
  AlertCircle,
  Star,
  Phone,
  Globe,
  Clock,
  MapPin,
  ChevronLeft,
  ChevronRight,
  ExternalLink,
} from "lucide-react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { useT } from "@/i18n";
import { cn } from "@/lib/utils";
import { getScoutRunResults, type ScoutRunProspect } from "@/api/scoutRuns";

const STATUS_DOT: Record<string, string> = {
  pending: "bg-zinc-400",
  running: "bg-amber-500 animate-pulse",
  completed: "bg-emerald-500",
  failed: "bg-red-500",
};

/** Safe hostname extraction: returns null on parse error or non-http(s). */
function safeHostname(website: string | null | undefined): string | null {
  if (!website) return null;
  if (!URL.canParse(website)) return null;
  try {
    const u = new URL(website);
    if (u.protocol !== "http:" && u.protocol !== "https:") return null;
    return u.hostname || null;
  } catch {
    return null;
  }
}

/** M3: coerce legacy query fields to display strings. */
function coerceQueryField(value: unknown): string {
  if (value == null) return "—";
  if (typeof value === "string") return value;
  if (typeof value === "number") return String(value);
  if (Array.isArray(value)) return value.map(coerceQueryField).join(", ");
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}

export function ScoutRunResultsPage() {
  const { id: runId } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const t = useT();

  const [data, setData] = useState<{
    run: {
      id: string;
      source: string;
      query: Record<string, unknown> | null;
      status: string;
      prospects_found: number;
      created_at: string | null;
      started_at: string | null;
      completed_at: string | null;
      error_message: string | null;
    };
    results: ScoutRunProspect[];
    total: number;
    page: number;
    per_page: number;
    pages: number;
  } | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(1);

  useEffect(() => {
    if (!runId) return;
    // I1: track the latest request so stale responses don't
    // overwrite fresh data. (Aborts the previous fetch via
    // a soft "cancelled" flag; the API client doesn't take
    // an AbortSignal yet.)
    let cancelled = false;
    // Sprint 4.1 followup: removed `localStorage.getItem("access_token")`.
    // The shared `api` axios instance handles auth via its interceptor
    // (including refresh-on-401). This was the C2 finding from the
    // holistic Sprint 4 review — three different auth patterns for
    // the same JWT, in the same sprint.
    setLoading(true);
    setError(null);
    getScoutRunResults(runId, page, 25)
      .then((d) => {
        if (cancelled) return;
        setData(d);
      })
      .catch((e) => {
        if (cancelled) return;
        setError(e.message);
      })
      .finally(() => {
        if (cancelled) return;
        setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [runId, page, navigate]);

  if (!runId) {
    return (
      <div className="container py-8">
        <p className="text-red-500">{t.scoutRun.errorMissingId}</p>
      </div>
    );
  }

  return (
    <div className="container py-6 space-y-6">
      <div className="flex items-center gap-3">
        <Button
          variant="ghost"
          size="icon"
          onClick={() => navigate(-1)}
          aria-label={t.common.back}
        >
          <ArrowLeft className="h-4 w-4" />
        </Button>
        <div>
          <h1 className="text-2xl font-semibold">
            {t.scoutRun.title} #{runId.slice(0, 8)}
          </h1>
          <p className="text-sm text-muted-foreground">{t.scoutRun.subtitle}</p>
        </div>
      </div>

      {loading && (
        <div className="space-y-3">
          <Skeleton className="h-24 w-full" />
          <Skeleton className="h-64 w-full" />
        </div>
      )}

      {error && (
        <Card className="border-red-200 bg-red-50">
          <CardContent className="pt-6 flex items-center gap-2 text-red-700">
            <AlertCircle className="h-4 w-4" />
            <span>{error}</span>
          </CardContent>
        </Card>
      )}

      {data && !loading && !error && (
        <>
          <RunHeader run={data.run} totalCount={data.total} />
          {/* I5 + M2: distinguish "0 results" from "out-of-range page" */}
          {data.total === 0 ? (
            <Card>
              <CardContent className="py-12 text-center text-muted-foreground">
                {t.scoutRun.empty}
              </CardContent>
            </Card>
          ) : data.results.length === 0 ? (
            <Card>
              <CardContent className="py-12 text-center text-muted-foreground">
                {t.scoutRun.outOfRange ?? t.scoutRun.empty}
              </CardContent>
            </Card>
          ) : (
            <ResultsTable results={data.results} />
          )}
          {data.pages > 1 && (
            <div className="flex items-center justify-between pt-2">
              <p className="text-sm text-muted-foreground">
                {t.scoutRun.paginationPageLabel
                  .replace("{page}", String(data.page))
                  .replace("{pages}", String(data.pages))}
              </p>
              <div className="flex items-center gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  disabled={data.page <= 1}
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                >
                  <ChevronLeft className="h-4 w-4" />
                  {t.scoutRun.paginationPrevious}
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  disabled={data.page >= data.pages}
                  onClick={() => setPage((p) => Math.min(data.pages, p + 1))}
                >
                  {t.scoutRun.paginationNext}
                  <ChevronRight className="h-4 w-4" />
                </Button>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}

function RunHeader({
  run,
  totalCount,
}: {
  run: {
    id: string;
    source: string;
    query: Record<string, unknown> | null;
    status: string;
    prospects_found: number;
    created_at: string | null;
    started_at: string | null;
    completed_at: string | null;
    error_message: string | null;
  };
  totalCount: number;
}) {
  const t = useT();
  // M3: coerce legacy query values
  const keywords = coerceQueryField(run.query?.keywords ?? run.query?.q);
  const location = coerceQueryField(run.query?.location);
  const maxResults = run.query?.max_results as number | undefined;
  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between gap-3">
          <div>
            <CardTitle className="text-base flex items-center gap-2">
              <span
                className={cn(
                  "inline-block w-2 h-2 rounded-full",
                  STATUS_DOT[run.status] || "bg-zinc-400",
                )}
              />
              {t.scoutRun[
                `status${run.status.charAt(0).toUpperCase()}${run.status.slice(1)}` as
                  | "statusPending" | "statusRunning" | "statusCompleted" | "statusFailed"
              ] || run.status}
            </CardTitle>
            <p className="text-sm text-muted-foreground mt-1">
              {run.source.toUpperCase()} · "{keywords}"
              {location && location !== "—" ? ` · ${location}` : ""}
              {maxResults ? ` · ${t.scoutRun.maxResults.replace("{n}", String(maxResults))}` : ""}
            </p>
          </div>
          <div className="text-right">
            <p className="text-2xl font-semibold">{totalCount}</p>
            <p className="text-xs text-muted-foreground">
              {t.scoutRun.resultsCountTotal}
            </p>
          </div>
        </div>
      </CardHeader>
    </Card>
  );
}

function ResultsTable({ results }: { results: ScoutRunProspect[] }) {
  const t = useT();
  const navigate = useNavigate();

  return (
    <Card>
      <CardContent className="p-0">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-muted/50 text-muted-foreground">
              <tr>
                <th className="text-left p-3 font-medium">
                  {t.scoutRun.colName}
                </th>
                <th className="text-left p-3 font-medium">
                  {t.scoutRun.colRating}
                </th>
                <th className="text-left p-3 font-medium">
                  {t.scoutRun.colReviewCount}
                </th>
                <th className="text-left p-3 font-medium">
                  {t.scoutRun.colHours}
                </th>
                <th className="text-left p-3 font-medium">
                  {t.scoutRun.colPhone}
                </th>
                <th className="text-left p-3 font-medium">
                  {t.scoutRun.colWebsite}
                </th>
              </tr>
            </thead>
            <tbody>
              {results.map((r) => {
                const rating = r.raw_data?.rating as number | undefined;
                const reviewCount = r.raw_data?.review_count as number | undefined;
                const hours = r.raw_data?.hours as string | undefined;
                // I2: safeHostname guards against malformed URLs
                // and rejects non-http(s) (M1: no mailto:/tel:/javascript:).
                const hostname = safeHostname(r.website);
                const address =
                  typeof r.raw_data?.raw_address === "string"
                    ? r.raw_data.raw_address
                    : null;
                return (
                  // M7: keyboard accessible — role=button, tabIndex,
                  // onKeyDown (Enter/Space → navigate). Was:
                  // <tr onClick={...}> with no keyboard path.
                  <tr
                    key={r.id}
                    role="button"
                    tabIndex={0}
                    onClick={() => navigate(`/prospects/${r.id}`)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter" || e.key === " ") {
                        e.preventDefault();
                        navigate(`/prospects/${r.id}`);
                      }
                    }}
                    className="border-t border-border hover:bg-muted/30 cursor-pointer focus:outline-none focus:ring-2 focus:ring-ring"
                  >
                    <td className="p-3">
                      <div className="font-medium">{r.company_name}</div>
                      {address && (
                        <div className="text-xs text-muted-foreground flex items-center gap-1 mt-0.5">
                          <MapPin className="h-3 w-3" aria-hidden="true" />
                          <span className="truncate max-w-[280px]">
                            {address}
                          </span>
                        </div>
                      )}
                    </td>
                    <td className="p-3 text-muted-foreground">
                      {rating != null ? (
                        <span className="inline-flex items-center gap-1">
                          <Star
                            className="h-3 w-3 fill-amber-400 text-amber-400"
                            aria-hidden="true"
                          />
                          {rating}
                        </span>
                      ) : (
                        <span className="text-xs">—</span>
                      )}
                    </td>
                    <td className="p-3 text-muted-foreground">
                      {reviewCount != null ? reviewCount.toLocaleString() : "—"}
                    </td>
                    <td className="p-3 text-muted-foreground">
                      {hours ? (
                        <span className="inline-flex items-center gap-1 text-xs">
                          <Clock className="h-3 w-3" aria-hidden="true" />
                          {hours}
                        </span>
                      ) : (
                        "—"
                      )}
                    </td>
                    <td className="p-3 text-muted-foreground">
                      {r.phone ? (
                        <span className="inline-flex items-center gap-1 text-xs">
                          <Phone className="h-3 w-3" aria-hidden="true" />
                          {r.phone}
                        </span>
                      ) : (
                        "—"
                      )}
                    </td>
                    <td className="p-3 text-muted-foreground">
                      {hostname ? (
                        // I4: full noopener+noreferrer
                        <a
                          href={r.website!}
                          target="_blank"
                          rel="noopener noreferrer"
                          onClick={(e) => e.stopPropagation()}
                          className="inline-flex items-center gap-1 text-xs hover:underline"
                        >
                          <Globe className="h-3 w-3" aria-hidden="true" />
                          <span className="truncate max-w-[160px]">
                            {hostname}
                          </span>
                          <ExternalLink className="h-3 w-3" aria-hidden="true" />
                        </a>
                      ) : (
                        "—"
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </CardContent>
    </Card>
  );
}
