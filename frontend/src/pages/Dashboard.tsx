import { useMemo } from "react";
import { Link } from "react-router-dom";
import {
  TrendingUp,
  Users,
  Star,
  Send,
  CheckCircle2,
  Sparkles,
  Activity,
} from "lucide-react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { StatCard } from "@/components/ui/stat-card";
import { StatusPill, GradePill } from "@/components/ui/status-pill";
import { EmptyState } from "@/components/ui/empty-state";
import { useProspects } from "@/hooks/useProspects";
import type { Prospect, ProspectStatus } from "@/types";

const STATUS_CHART_COLORS: Record<string, string> = {
  new: "#64748b",
  enriching: "#3b82f6",
  scored: "#8b5cf6",
  approved: "#6366f1",
  contacted: "#f59e0b",
  replied: "#f97316",
  won: "#059669",
  lost: "#f43f5e",
  archived: "#71717a",
};

export function DashboardPage() {
  const { data, isLoading, isError } = useProspects({ per_page: 100 });

  const stats = useMemo(() => {
    const prospects: Prospect[] = data?.items ?? [];
    const total = data?.total ?? 0;
    const hot = prospects.filter(
      (p) => p.score_total != null && p.score_total >= 80,
    ).length;
    const contacted = prospects.filter(
      (p) => p.status === "contacted" || p.status === "replied",
    ).length;
    const won = prospects.filter((p) => p.status === "won").length;
    return { total, hot, contacted, won, prospects };
  }, [data]);

  const chartData = useMemo(() => {
    const counts: Partial<Record<ProspectStatus, number>> = {};
    stats.prospects.forEach((p) => {
      counts[p.status] = (counts[p.status] ?? 0) + 1;
    });
    return Object.entries(counts)
      .filter(([_, v]) => (v ?? 0) > 0)
      .map(([status, count]) => ({
        status,
        count: count ?? 0,
        fill: STATUS_CHART_COLORS[status] ?? "#94a3b8",
      }));
  }, [stats.prospects]);

  // Grade distribution for donut
  const gradeData = useMemo(() => {
    const counts: Record<string, number> = { A: 0, B: 0, C: 0, D: 0 };
    stats.prospects.forEach((p) => {
      if (p.quality_grade) counts[p.quality_grade] = (counts[p.quality_grade] ?? 0) + 1;
    });
    return [
      { name: "A", value: counts.A, fill: "#059669" },
      { name: "B", value: counts.B, fill: "#0ea5e9" },
      { name: "C", value: counts.C, fill: "#f59e0b" },
      { name: "D", value: counts.D, fill: "#f43f5e" },
    ].filter((g) => g.value > 0);
  }, [stats.prospects]);

  // Top prospects (by score)
  const topProspects = useMemo(() => {
    return [...stats.prospects]
      .filter((p) => p.score_total != null)
      .sort((a, b) => (b.score_total ?? 0) - (a.score_total ?? 0))
      .slice(0, 5);
  }, [stats.prospects]);

  return (
    <div className="space-y-8 animate-fade-in">
      {/* Hero header */}
      <div className="flex flex-col md:flex-row md:items-end md:justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-2">
            <div className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse" />
            <span className="text-xs text-muted-foreground uppercase tracking-wider font-medium">
              Live · {new Date().toLocaleDateString("id-ID", { weekday: "long", day: "numeric", month: "long" })}
            </span>
          </div>
          <h1 className="text-4xl font-bold tracking-tight">
            Welcome back
          </h1>
          <p className="text-muted-foreground mt-2 max-w-2xl">
            Here's what's happening with your lead generation pipeline today.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" asChild>
            <Link to="/pipeline">View pipeline</Link>
          </Button>
          <Button asChild>
            <Link to="/prospects">
              <Sparkles className="h-4 w-4" />
              New search
            </Link>
          </Button>
        </div>
      </div>

      {/* Stats grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {isLoading ? (
          <>
            <Skeleton className="h-32" />
            <Skeleton className="h-32" />
            <Skeleton className="h-32" />
            <Skeleton className="h-32" />
          </>
        ) : (
          <>
            <StatCard
              title="Total Prospects"
              value={stats.total}
              description="All time"
              icon={<Users className="h-4 w-4" />}
            />
            <StatCard
              title="Hot Leads"
              value={stats.hot}
              description="Score 80+"
              icon={<Star className="h-4 w-4" />}
            />
            <StatCard
              title="Contacted"
              value={stats.contacted}
              description="Outreach sent"
              icon={<Send className="h-4 w-4" />}
            />
            <StatCard
              title="Won"
              value={stats.won}
              description="Converted to clients"
              icon={<CheckCircle2 className="h-4 w-4" />}
            />
          </>
        )}
      </div>

      {/* Charts row */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Pipeline by status bar chart */}
        <Card className="lg:col-span-2 overflow-hidden">
          <CardHeader>
            <div className="flex items-start justify-between">
              <div>
                <CardTitle className="text-lg">Pipeline by status</CardTitle>
                <CardDescription>
                  Distribution of all discovered prospects
                </CardDescription>
              </div>
              <Button variant="ghost" size="sm" asChild>
                <Link to="/pipeline">View all</Link>
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <Skeleton className="h-72 w-full" />
            ) : isError ? (
              <EmptyState
                className="h-72"
                icon={<Activity className="h-5 w-5" />}
                title="Could not load prospects"
                description="Check your connection or sign in again"
              />
            ) : chartData.length === 0 ? (
              <EmptyState
                className="h-72 px-4"
                icon={<Sparkles className="h-5 w-5" />}
                title="No data yet"
                description="Run a scout job in T4 to populate this chart"
                action={
                  <Button size="sm" className="mt-2">
                    Run first scout
                  </Button>
                }
              />
            ) : (
              <ResponsiveContainer width="100%" height={288}>
                <BarChart data={chartData} margin={{ top: 5, right: 5, left: 0, bottom: 5 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" vertical={false} />
                  <XAxis
                    dataKey="status"
                    tick={{ fill: "hsl(var(--muted-foreground))", fontSize: 11 }}
                    axisLine={false}
                    tickLine={false}
                    tickFormatter={(v) => v.charAt(0).toUpperCase() + v.slice(1)}
                  />
                  <YAxis
                    allowDecimals={false}
                    tick={{ fill: "hsl(var(--muted-foreground))", fontSize: 11 }}
                    axisLine={false}
                    tickLine={false}
                  />
                  <Tooltip
                    cursor={{ fill: "hsl(var(--muted))", opacity: 0.5 }}
                    contentStyle={{
                      backgroundColor: "hsl(var(--popover))",
                      border: "1px solid hsl(var(--border))",
                      borderRadius: "0.625rem",
                      fontSize: "12px",
                      padding: "0.5rem 0.75rem",
                      boxShadow:
                        "0 4px 6px -1px rgb(0 0 0 / 0.08), 0 2px 4px -2px rgb(0 0 0 / 0.05)",
                      color: "hsl(var(--popover-foreground))",
                    }}
                    labelStyle={{
                      fontWeight: 600,
                      marginBottom: 4,
                      textTransform: "capitalize",
                    }}
                    itemStyle={{ padding: 0 }}
                  />
                  <Bar dataKey="count" radius={[6, 6, 0, 0]}>
                    {chartData.map((entry) => (
                      <Cell key={entry.status} fill={entry.fill} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            )}
          </CardContent>
        </Card>

        {/* Grade distribution donut */}
        <Card className="overflow-hidden">
          <CardHeader>
            <CardTitle className="text-lg">Lead quality</CardTitle>
            <CardDescription>Distribution by grade</CardDescription>
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <Skeleton className="h-72 w-full" />
            ) : gradeData.length === 0 ? (
              <EmptyState
                className="h-72"
                icon={<TrendingUp className="h-5 w-5" />}
                title="No grades yet"
                description="Leads will be scored automatically"
              />
            ) : (
              <div className="flex flex-col items-center">
                <ResponsiveContainer width="100%" height={200}>
                  <PieChart>
                    <Pie
                      data={gradeData}
                      cx="50%"
                      cy="50%"
                      innerRadius={50}
                      outerRadius={80}
                      paddingAngle={2}
                      dataKey="value"
                    />
                  </PieChart>
                </ResponsiveContainer>
                <div className="flex flex-wrap gap-2 mt-2 justify-center">
                  {gradeData.map((g) => (
                    <div key={g.name} className="flex items-center gap-1.5 text-xs">
                      <span
                        className="h-2 w-2 rounded-full"
                        style={{ backgroundColor: g.fill }}
                      />
                      <span className="text-muted-foreground">
                        {g.name}: {g.value}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Top prospects table */}
      <Card>
        <CardHeader>
          <div className="flex items-start justify-between">
            <div>
              <CardTitle className="text-lg">Top prospects</CardTitle>
              <CardDescription>
                Highest-scoring leads, ready for outreach
              </CardDescription>
            </div>
            <Button variant="ghost" size="sm" asChild>
              <Link to="/prospects">View all →</Link>
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="space-y-2">
              {Array.from({ length: 3 }).map((_, i) => (
                <Skeleton key={i} className="h-12" />
              ))}
            </div>
          ) : topProspects.length === 0 ? (
            <EmptyState
              className="py-12"
              icon={<Users className="h-5 w-5" />}
              title="No prospects yet"
              description="Run a scout job to discover businesses that match your ICP"
              action={
                <Button size="sm" className="mt-2">
                  Start prospecting
                </Button>
              }
            />
          ) : (
            <div className="overflow-x-auto -mx-6">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b">
                    <th className="text-left font-medium text-muted-foreground px-6 py-2.5">Company</th>
                    <th className="text-left font-medium text-muted-foreground px-3 py-2.5">Industry</th>
                    <th className="text-left font-medium text-muted-foreground px-3 py-2.5">Status</th>
                    <th className="text-right font-medium text-muted-foreground px-3 py-2.5">Score</th>
                    <th className="text-right font-medium text-muted-foreground px-6 py-2.5">Grade</th>
                  </tr>
                </thead>
                <tbody>
                  {topProspects.map((p) => (
                    <tr
                      key={p.id}
                      className="border-b last:border-0 hover:bg-muted/30 transition-colors"
                    >
                      <td className="px-6 py-3 font-medium">{p.company_name}</td>
                      <td className="px-3 py-3 text-muted-foreground capitalize">
                        {p.industry ?? "—"}
                      </td>
                      <td className="px-3 py-3">
                        <StatusPill status={p.status} />
                      </td>
                      <td className="px-3 py-3 text-right num font-semibold">
                        {p.score_total}
                      </td>
                      <td className="px-6 py-3 text-right">
                        {p.quality_grade && <GradePill grade={p.quality_grade} />}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
