import { useState } from "react";
import { Search, Filter, MoreHorizontal, Plus } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { StatusPill, GradePill } from "@/components/ui/status-pill";
import { useProspects } from "@/hooks/useProspects";
import type { ProspectStatus } from "@/types";
import { cn } from "@/lib/utils";

const STATUS_FILTERS: { label: string; value: ProspectStatus | "all" }[] = [
  { label: "All", value: "all" },
  { label: "New", value: "new" },
  { label: "Scored", value: "scored" },
  { label: "Contacted", value: "contacted" },
  { label: "Replied", value: "replied" },
  { label: "Won", value: "won" },
  { label: "Lost", value: "lost" },
];

const PAGE_SIZE = 20;

export function ProspectsPage() {
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<ProspectStatus | "all">("all");
  const [page, setPage] = useState(1);

  const { data, isLoading, isError } = useProspects({
    page,
    per_page: PAGE_SIZE,
    status: statusFilter === "all" ? undefined : statusFilter,
    search: search || undefined,
  });

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Hero header */}
      <div className="flex flex-col md:flex-row md:items-end md:justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Prospects</h1>
          <p className="text-muted-foreground mt-2">
            {data?.total ?? 0} total · {data?.items.length ?? 0} in view
          </p>
        </div>
        <div className="flex items-center gap-2">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Search by company, email..."
              value={search}
              onChange={(e) => {
                setSearch(e.target.value);
                setPage(1);
              }}
              className="h-10 pl-9 w-64"
            />
          </div>
          <Button>
            <Plus className="h-4 w-4" />
            New search
          </Button>
        </div>
      </div>

      {/* Filter chips */}
      <div className="flex items-center gap-2 overflow-x-auto pb-1">
        {STATUS_FILTERS.map((f) => (
          <button
            key={f.value}
            type="button"
            onClick={() => {
              setStatusFilter(f.value);
              setPage(1);
            }}
            className={cn(
              "px-3 py-1.5 rounded-full text-sm font-medium transition-all duration-150 ease-out-expo border whitespace-nowrap",
              statusFilter === f.value
                ? "bg-foreground text-background border-foreground"
                : "bg-background text-muted-foreground border-border hover:text-foreground hover:border-foreground/30",
            )}
          >
            {f.label}
          </button>
        ))}
      </div>

      {/* Table */}
      <Card className="overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b bg-muted/30">
                <th className="text-left font-medium text-muted-foreground px-6 py-3 text-xs uppercase tracking-wider">
                  Company
                </th>
                <th className="text-left font-medium text-muted-foreground px-3 py-3 text-xs uppercase tracking-wider">
                  Industry
                </th>
                <th className="text-left font-medium text-muted-foreground px-3 py-3 text-xs uppercase tracking-wider">
                  Location
                </th>
                <th className="text-left font-medium text-muted-foreground px-3 py-3 text-xs uppercase tracking-wider">
                  Status
                </th>
                <th className="text-right font-medium text-muted-foreground px-3 py-3 text-xs uppercase tracking-wider">
                  Score
                </th>
                <th className="text-right font-medium text-muted-foreground px-6 py-3 text-xs uppercase tracking-wider">
                  Grade
                </th>
                <th className="w-10"></th>
              </tr>
            </thead>
            <tbody>
              {isLoading ? (
                Array.from({ length: 5 }).map((_, i) => (
                  <tr key={i} className="border-b last:border-0">
                    <td className="px-6 py-3">
                      <Skeleton className="h-4 w-32" />
                    </td>
                    <td className="px-3 py-3">
                      <Skeleton className="h-4 w-20" />
                    </td>
                    <td className="px-3 py-3">
                      <Skeleton className="h-4 w-24" />
                    </td>
                    <td className="px-3 py-3">
                      <Skeleton className="h-5 w-20" />
                    </td>
                    <td className="px-3 py-3 text-right">
                      <Skeleton className="h-4 w-10 ml-auto" />
                    </td>
                    <td className="px-6 py-3 text-right">
                      <Skeleton className="h-5 w-8 ml-auto" />
                    </td>
                    <td></td>
                  </tr>
                ))
              ) : isError ? (
                <tr>
                  <td colSpan={7} className="px-6 py-12 text-center">
                    <p className="text-sm text-destructive">
                      Could not load prospects. Check your connection.
                    </p>
                  </td>
                </tr>
              ) : data?.items.length === 0 ? (
                <tr>
                  <td colSpan={7} className="px-6 py-16 text-center">
                    <div className="h-12 w-12 rounded-full bg-muted flex items-center justify-center text-muted-foreground mx-auto mb-3">
                      <Filter className="h-5 w-5" />
                    </div>
                    <p className="text-sm font-medium">No prospects found</p>
                    <p className="text-xs text-muted-foreground mt-1 max-w-xs mx-auto">
                      {search
                        ? `No results for "${search}". Try a different search term.`
                        : "Run a scout job to discover businesses that need software services."}
                    </p>
                    <Button className="mt-4" size="sm">
                      <Plus className="h-4 w-4" />
                      Start prospecting
                    </Button>
                  </td>
                </tr>
              ) : (
                data?.items.map((p) => (
                  <tr
                    key={p.id}
                    className="border-b last:border-0 hover:bg-muted/30 transition-colors cursor-pointer"
                  >
                    <td className="px-6 py-3">
                      <div className="flex items-center gap-3">
                        <div className="h-8 w-8 rounded-md bg-gradient-to-br from-violet-500/20 to-indigo-500/10 border border-violet-200/50 flex items-center justify-center text-violet-700 font-semibold text-sm">
                          {p.company_name.charAt(0).toUpperCase()}
                        </div>
                        <div>
                          <p className="font-medium">{p.company_name}</p>
                          {p.email && (
                            <p className="text-xs text-muted-foreground">
                              {p.email}
                            </p>
                          )}
                        </div>
                      </div>
                    </td>
                    <td className="px-3 py-3 text-muted-foreground capitalize">
                      {p.industry ?? "—"}
                    </td>
                    <td className="px-3 py-3 text-muted-foreground">
                      {p.location_city ?? "—"}
                    </td>
                    <td className="px-3 py-3">
                      <StatusPill status={p.status} />
                    </td>
                    <td className="px-3 py-3 text-right num font-semibold">
                      {p.score_total ?? "—"}
                    </td>
                    <td className="px-6 py-3 text-right">
                      {p.quality_grade ? (
                        <GradePill grade={p.quality_grade} />
                      ) : (
                        <span className="text-muted-foreground text-xs">—</span>
                      )}
                    </td>
                    <td className="px-3 py-3">
                      <Button variant="ghost" size="icon" className="h-7 w-7">
                        <MoreHorizontal className="h-4 w-4" />
                      </Button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        {data && data.pages > 1 && (
          <div className="flex items-center justify-between border-t px-6 py-3 text-sm">
            <p className="text-muted-foreground">
              Page {data.page} of {data.pages}
            </p>
            <div className="flex gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page === 1}
              >
                Previous
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setPage((p) => Math.min(data.pages, p + 1))}
                disabled={page >= data.pages}
              >
                Next
              </Button>
            </div>
          </div>
        )}
      </Card>
    </div>
  );
}
