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
  Target,
  TrendingDown,
} from "lucide-react";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { StatCard } from "@/components/ui/stat-card";
import { StatusPill, GradePill } from "@/components/ui/status-pill";
import { EmptyState } from "@/components/ui/empty-state";
import { PipelineFunnel } from "@/components/charts/PipelineFunnel";
import { GradeDonut } from "@/components/charts/GradeDonut";
import { useProspects } from "@/hooks/useProspects";
import type { Prospect, ProspectStatus } from "@/types";

// Per playbook §1: status colors
const FUNNEL_STAGES = [
  {
    key: "new",
    label: "New",
    dotColor: "bg-slate-500",
    barColor: "bg-gradient-to-r from-slate-500 to-slate-400",
  },
  {
    key: "enriching",
    label: "Enriching",
    dotColor: "bg-blue-500",
    barColor: "bg-gradient-to-r from-blue-500 to-blue-400",
  },
  {
    key: "scored",
    label: "Scored",
    dotColor: "bg-violet-500",
    barColor: "bg-gradient-to-r from-violet-500 to-violet-400",
  },
  {
    key: "approved",
    label: "Approved",
    dotColor: "bg-indigo-500",
    barColor: "bg-gradient-to-r from-indigo-500 to-indigo-400",
  },
  {
    key: "contacted",
    label: "Contacted",
    dotColor: "bg-amber-500",
    barColor: "bg-gradient-to-r from-amber-500 to-amber-400",
  },
  {
    key: "replied",
    label: "Replied",
    dotColor: "bg-orange-500",
    barColor: "bg-gradient-to-r from-orange-500 to-orange-400",
  },
  {
    key: "won",
    label: "Won",
    dotColor: "bg-emerald-500",
    barColor: "bg-gradient-to-r from-emerald-500 to-emerald-400",
    emoji: "🎉",
  },
];

const GRADE_COLORS: Record<string, string> = {
  A: "#059669",
  B: "#0ea5e9",
  C: "#f59e0b",
  D: "#f43f5e",
};

// Generate realistic-looking sparkline data (until T7 has real time-series)
function genSparkline(seed: number, trend: "up" | "down" | "stable"): number[] {
  const rng = (n: number) => Math.sin(seed * n) * 0.5 + 0.5;
  const base = Array.from({ length: 14 }, (_, i) => rng(i + 1) * 10 + 5);
  if (trend === "up") return base.map((v, i) => v + i * 0.5);
  if (trend === "down") return base.map((v, i) => v - i * 0.4);
  return base;
}

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

  const funnelData = useMemo(() => {
    return FUNNEL_STAGES.map((stage) => ({
      ...stage,
      count: stats.prospects.filter((p) => p.status === stage.key).length,
    }));
  }, [stats.prospects]);

  const hasAnyData = stats.total > 0;

  const gradeData = useMemo(() => {
    const counts: Record<string, number> = { A: 0, B: 0, C: 0, D: 0 };
    stats.prospects.forEach((p) => {
      if (p.quality_grade) counts[p.quality_grade] = (counts[p.quality_grade] ?? 0) + 1;
    });
    return (["A", "B", "C", "D"] as const)
      .map((g) => ({
        name: g,
        value: counts[g],
        color: GRADE_COLORS[g],
      }))
      .filter((g) => g.value > 0);
  }, [stats.prospects]);

  const topProspects = useMemo(() => {
    return [...stats.prospects]
      .filter((p) => p.score_total != null)
      .sort((a, b) => (b.score_total ?? 0) - (a.score_total ?? 0))
      .slice(0, 5);
  }, [stats.prospects]);

  // Conversion rate: % of total that reached Won
  const wonRate =
    stats.total > 0
      ? Math.round((stats.won / stats.total) * 100)
      : 0;
  // Pipeline activation: % past "new" status
  const activatedRate =
    stats.total > 0
      ? Math.round(
          (stats.prospects.filter((p) => p.status !== "new").length /
            stats.total) *
            100,
        )
      : 0;

  return (
    <div className="space-y-8 animate-fade-in">
      {/* Hero header */}
      <div className="flex flex-col md:flex-row md:items-end md:justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-2">
            <div className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse" />
            <span className="text-xs text-muted-foreground uppercase tracking-wider font-medium">
              Live ·{" "}
              {new Date().toLocaleDateString("id-ID", {
                weekday: "long",
                day: "numeric",
                month: "long",
              })}
            </span>
          </div>
          <h1 className="text-4xl font-bold tracking-tight">Welcome back</h1>
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

      {/* Stats grid + Conversion highlights */}
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
              sparkline={genSparkline(1, "up")}
              sparklineColor="text-violet-500"
            />
            <StatCard
              title="Hot Leads"
              value={stats.hot}
              description="Score 80+"
              icon={<Star className="h-4 w-4" />}
              sparkline={genSparkline(2, "up")}
              sparklineColor="text-amber-500"
            />
            <StatCard
              title="Contacted"
              value={stats.contacted}
              description="Outreach sent"
              icon={<Send className="h-4 w-4" />}
              sparkline={genSparkline(3, "stable")}
              sparklineColor="text-blue-500"
            />
            <StatCard
              title="Won"
              value={stats.won}
              description={`${wonRate}% conversion`}
              icon={<CheckCircle2 className="h-4 w-4" />}
              sparkline={genSparkline(4, "up")}
              sparklineColor="text-emerald-500"
            />
          </>
        )}
      </div>

      {/* Hero chart row: Pipeline Funnel + Lead Quality */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Pipeline Funnel — the new centerpiece (replaces boring bar chart) */}
        <Card className="lg:col-span-2">
          <CardHeader>
            <div className="flex items-start justify-between">
              <div>
                <CardTitle className="text-lg flex items-center gap-2">
                  <Target className="h-4 w-4 text-muted-foreground" />
                  Pipeline funnel
                </CardTitle>
                <CardDescription>
                  Prospects moving through each stage, with conversion rates
                </CardDescription>
              </div>
              <Button variant="ghost" size="sm" asChild>
                <Link to="/pipeline">View all</Link>
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <div className="space-y-3">
                {Array.from({ length: 5 }).map((_, i) => (
                  <Skeleton key={i} className="h-9" />
                ))}
              </div>
            ) : isError ? (
              <EmptyState
                className="py-12"
                icon={<Activity className="h-5 w-5" />}
                title="Could not load prospects"
                description="Check your connection or sign in again"
              />
            ) : !hasAnyData ? (
              <EmptyState
                className="py-12"
                icon={<Sparkles className="h-5 w-5" />}
                title="No prospects yet"
                description="Run a scout job in T4 to populate this funnel"
                action={
                  <Button size="sm" className="mt-2">
                    Run first scout
                  </Button>
                }
              />
            ) : (
              <PipelineFunnel stages={funnelData} />
            )}
          </CardContent>
        </Card>

        {/* Grade Donut with center label */}
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Lead quality</CardTitle>
            <CardDescription>Distribution by grade</CardDescription>
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <Skeleton className="h-48 w-full" />
            ) : (
              <GradeDonut
                data={gradeData}
                centerSubLabel="total"
              />
            )}
          </CardContent>
        </Card>
      </div>

      {/* Pipeline activation + Source distribution row */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <ConversionCard
          title="Pipeline activation"
          value={activatedRate}
          description="% of prospects that have moved past the 'New' stage"
          icon={<TrendingUp className="h-4 w-4" />}
          positive={activatedRate >= 50}
        />
        <ConversionCard
          title="Win rate"
          value={wonRate}
          description="% of total prospects that closed as won"
          icon={<CheckCircle2 className="h-4 w-4" />}
          positive={wonRate >= 10}
        />
        <ConversionCard
          title="Drop-off"
          value={
            stats.total > 0
              ? Math.round(
                  ((stats.total - stats.prospects.filter((p) => p.status !== "lost").length) /
                    stats.total) *
                    100,
                )
              : 0
          }
          description="% of prospects marked as Lost"
          icon={<TrendingDown className="h-4 w-4" />}
          positive={false}
          inverse
        />
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

interface ConversionCardProps {
  title: string;
  value: number;
  description: string;
  icon: React.ReactNode;
  positive: boolean;
  inverse?: boolean;
}

function ConversionCard({
  title,
  value,
  description,
  icon,
  positive,
  inverse = false,
}: ConversionCardProps) {
  // For "drop-off" card, lower is better
  const isGood = inverse ? !positive : positive;
  const colorClass = isGood ? "text-emerald-600" : "text-rose-600";
  const bgClass = isGood
    ? "from-emerald-500/10 to-emerald-500/5"
    : "from-rose-500/10 to-rose-500/5";

  return (
    <Card
      className={`relative overflow-hidden bg-gradient-to-br ${bgClass}`}
    >
      <CardContent className="p-5">
        <div className="flex items-center justify-between mb-2">
          <span className="text-xs uppercase tracking-wider font-medium text-muted-foreground">
            {title}
          </span>
          <div className="h-8 w-8 rounded-lg bg-card flex items-center justify-center text-muted-foreground">
            {icon}
          </div>
        </div>
        <div className="flex items-baseline gap-1">
          <span className={`text-3xl font-bold num ${colorClass}`}>{value}</span>
          <span className="text-lg text-muted-foreground">%</span>
        </div>
        <p className="text-xs text-muted-foreground mt-1.5 leading-relaxed">
          {description}
        </p>
      </CardContent>
    </Card>
  );
}
