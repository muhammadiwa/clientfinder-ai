/**
 * ScoutRunResults — Layer 2 of the hybrid C display (Sprint 4 PR 3).
 *
 * Dedicated page at /scout-runs/:id/results showing the FULL raw
 * data from a ScoutRun. ProspectDetail (Layer 1) shows a 1-line
 * breadcrumb link to this page; the actual payload lives here.
 *
 * The page is paginated (25 per page default), sortable by the
 * raw_data fields (rating, review_count, hours), and deep-linkable.
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
    const token = localStorage.getItem("access_token") || "";
    setLoading(true);
    setError(null);
    getScoutRunResults(runId, page, 25, token)
      .then(setData)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [runId, page]);

  if (!runId) {
    return (
      <div className="container py-8">
        <p className="text-red-500">{t.scoutRun.error.missingId}</p>
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
          <ResultsTable results={data.results} />
          {data.pages > 1 && (
            <div className="flex items-center justify-between pt-2">
              <p className="text-sm text-muted-foreground">
                {t.scoutRun.pagination.pageLabel
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
                  {t.scoutRun.pagination.previous}
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  disabled={data.page >= data.pages}
                  onClick={() => setPage((p) => Math.min(data.pages, p + 1))}
                >
                  {t.scoutRun.pagination.next}
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
  const keywords = (run.query?.keywords as string) || (run.query?.q as string) || "—";
  const location = (run.query?.location as string) || "";
  const maxResults = (run.query?.max_results as number) || null;
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
              {t.scoutRun.statusLabels[run.status as keyof typeof t.scoutRun.statusLabels] ||
                run.status}
            </CardTitle>
            <p className="text-sm text-muted-foreground mt-1">
              {run.source.toUpperCase()} · "{keywords}"
              {location ? ` · ${location}` : ""}
              {maxResults ? ` · ${t.scoutRun.maxResults.replace("{n}", String(maxResults))}` : ""}
            </p>
          </div>
          <div className="text-right">
            <p className="text-2xl font-semibold">{totalCount}</p>
            <p className="text-xs text-muted-foreground">
              {t.scoutRun.resultsCount}
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

  if (results.length === 0) {
    return (
      <Card>
        <CardContent className="py-12 text-center text-muted-foreground">
          {t.scoutRun.empty}
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardContent className="p-0">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-muted/50 text-muted-foreground">
              <tr>
                <th className="text-left p-3 font-medium">
                  {t.scoutRun.tableHeaders.name}
                </th>
                <th className="text-left p-3 font-medium">
                  {t.scoutRun.tableHeaders.rating}
                </th>
                <th className="text-left p-3 font-medium">
                  {t.scoutRun.tableHeaders.reviewCount}
                </th>
                <th className="text-left p-3 font-medium">
                  {t.scoutRun.tableHeaders.hours}
                </th>
                <th className="text-left p-3 font-medium">
                  {t.scoutRun.tableHeaders.phone}
                </th>
                <th className="text-left p-3 font-medium">
                  {t.scoutRun.tableHeaders.website}
                </th>
              </tr>
            </thead>
            <tbody>
              {results.map((r) => {
                const rating = r.raw_data?.rating as number | undefined;
                const reviewCount = r.raw_data?.review_count as number | undefined;
                const hours = r.raw_data?.hours as string | undefined;
                return (
                  <tr
                    key={r.id}
                    onClick={() => navigate(`/prospects/${r.id}`)}
                    className="border-t border-border hover:bg-muted/30 cursor-pointer"
                  >
                    <td className="p-3">
                      <div className="font-medium">{r.company_name}</div>
                      {typeof r.raw_data?.raw_address === "string" && (
                        <div className="text-xs text-muted-foreground flex items-center gap-1 mt-0.5">
                          <MapPin className="h-3 w-3" />
                          <span className="truncate max-w-[280px]">
                            {String(r.raw_data.raw_address)}
                          </span>
                        </div>
                      )}
                    </td>
                    <td className="p-3 text-muted-foreground">
                      {rating != null ? (
                        <span className="inline-flex items-center gap-1">
                          <Star className="h-3 w-3 fill-amber-400 text-amber-400" />
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
                          <Clock className="h-3 w-3" />
                          {hours}
                        </span>
                      ) : (
                        "—"
                      )}
                    </td>
                    <td className="p-3 text-muted-foreground">
                      {r.phone ? (
                        <span className="inline-flex items-center gap-1 text-xs">
                          <Phone className="h-3 w-3" />
                          {r.phone}
                        </span>
                      ) : (
                        "—"
                      )}
                    </td>
                    <td className="p-3 text-muted-foreground">
                      {r.website ? (
                        <a
                          href={r.website}
                          target="_blank"
                          rel="noreferrer"
                          onClick={(e) => e.stopPropagation()}
                          className="inline-flex items-center gap-1 text-xs hover:underline"
                        >
                          <Globe className="h-3 w-3" />
                          <span className="truncate max-w-[160px]">
                            {new URL(r.website).hostname}
                          </span>
                          <ExternalLink className="h-3 w-3" />
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
