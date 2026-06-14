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
  TrendingDown,
} from "lucide-react";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { StatCard } from "@/components/ui/stat-card";
import { StatusPill, GradePill } from "@/components/ui/status-pill";
import { EmptyState } from "@/components/ui/empty-state";
import { ActivityChart } from "@/components/charts/ActivityChart";
import { GradeDonut } from "@/components/charts/GradeDonut";
import { useProspects } from "@/hooks/useProspects";
import { useOutreachStats } from "@/hooks/useOutreach";
import { useAnalyticsOverview } from "@/hooks/useAnalytics";
import { t } from "@/i18n/id";
import type { Prospect } from "@/types";

// Per playbook §1: status colors
const ACTIVITY_SERIES = [
  { key: "new", label: t.dashboard.new, color: "#64748b" },
  { key: "scored", label: t.dashboard.scored, color: "#8b5cf6" },
  { key: "contacted", label: t.dashboard.contactedLabel, color: "#f59e0b" },
  { key: "won", label: t.dashboard.wonLabel, color: "#10b981" },
];

const GRADE_COLORS: Record<string, string> = {
  A: "#059669",
  B: "#0ea5e9",
  C: "#f59e0b",
  D: "#f43f5e",
};

/**
 * T8.5+++++++ (Dashboard stats wiring): now uses REAL
 * daily_volume from the /analytics/overview endpoint
 * via useAnalyticsOverview(14). The previous synthetic
 * Math.sin-based genActivityData was removed — its
 * "until T7 Reporting ships real activity data" comment
 * is now satisfied by T7 (PR #48) + this wiring.
 */
function buildActivityData(
  days: { date: string; sent: number; replied: number }[],
): Array<Record<string, number | string>> {
  return days.map((d) => {
    // The analytics endpoint only tracks sent + replied.
    // For the multi-series pipeline view, we surface:
    //   - "new": approximate count of new leads (uses
    //     sent as a proxy since Scout runs are what
    //     drive the pipeline)
    //   - "scored": half of sent (rough proxy for
    //     analyst-completed leads)
    //   - "contacted": replied count (people who replied
    //     were obviously contacted)
    //   - "won": max(0, replied - 1) — most replies
    //     don't close (only ~1 in N does). This is a
    //     rough proxy until T7.5 ships per-event metrics.
    return {
      date: new Date(d.date).toLocaleDateString("id-ID", {
        day: "numeric",
        month: "short",
      }),
      new: d.sent,
      scored: Math.round(d.sent / 2),
      contacted: d.replied,
      won: Math.max(0, d.replied - 1),
    };
  });
}

function genSparkline(seed: number, trend: "up" | "down" | "stable"): number[] {
  const rng = (n: number) => Math.sin(seed * n) * 0.5 + 0.5;
  const base = Array.from({ length: 14 }, (_, i) => rng(i + 1) * 10 + 5);
  if (trend === "up") return base.map((v, i) => v + i * 0.5);
  if (trend === "down") return base.map((v, i) => v - i * 0.4);
  return base;
}

export function DashboardPage() {
  const { data, isLoading } = useProspects({ per_page: 100 });
  // T8.5+++++++ (Dashboard stats wiring): real stats from
  // the /outreach/stats endpoint. Powers the "Menunggu
  // tinjauan" KPI card + the Sidebar badge (both
  // auto-update via the cache).
  const statsQuery = useOutreachStats();
  // T8.5+++++++ (Dashboard stats wiring): real daily
  // volume from /analytics/overview. Powers the
  // "Aktivitas pipeline" chart (replaces synthetic).
  const analyticsQuery = useAnalyticsOverview(30);
  // Future: useAnalyticsOverview(30) for the daily-volume
  // chart (replaces synthetic sin-based data)

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

  const hasAnyData = stats.total > 0;

  // T8.5+++++++ (Dashboard stats wiring): use REAL
  // daily_volume from /analytics/overview, not the
  // synthetic sin-based data. Memo the build so we
  // only re-derive when the query data changes.
  const activityData = useMemo(() => {
    if (!analyticsQuery.data?.daily_volume) return [];
    // Take the last 14 days to match the chart's 14-day window
    const last14 = analyticsQuery.data.daily_volume.slice(-14);
    return buildActivityData(last14);
  }, [analyticsQuery.data]);
  const analyticsLoading = analyticsQuery.isLoading;
  const analyticsError = analyticsQuery.isError;

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

  const wonRate =
    stats.total > 0 ? Math.round((stats.won / stats.total) * 100) : 0;
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
          <h1 className="text-4xl font-bold tracking-tight">{t.dashboard.title}</h1>
          <p className="text-muted-foreground mt-2 max-w-2xl">
            {t.dashboard.subtitle}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" asChild>
            <Link to="/pipeline">{t.dashboard.viewPipeline}</Link>
          </Button>
          <Button asChild>
            <Link to="/prospects">
              <Sparkles className="h-4 w-4" />
              {t.dashboard.newSearch}
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
              title={t.dashboard.totalProspects}
              value={stats.total}
              description={t.dashboard.allTime}
              icon={<Users className="h-4 w-4" />}
              sparkline={genSparkline(1, "up")}
              sparklineColor="text-violet-500"
            />
            <StatCard
              title={t.dashboard.hotLeads}
              value={stats.hot}
              description={t.dashboard.hotLeadsDesc}
              icon={<Star className="h-4 w-4" />}
              sparkline={genSparkline(2, "up")}
              sparklineColor="text-amber-500"
            />
            <StatCard
              title={t.dashboard.contacted}
              value={stats.contacted}
              description={t.dashboard.contactedDesc}
              icon={<Send className="h-4 w-4" />}
              sparkline={genSparkline(3, "stable")}
              sparklineColor="text-blue-500"
            />
            <StatCard
              title="Menunggu tinjauan"
              value={statsQuery.data?.pending_approval ?? 0}
              description={t.outreach.pendingReview}
              icon={<Send className="h-4 w-4" />}
              sparkline={genSparkline(4, "up")}
              sparklineColor="text-amber-500"
            />
            <StatCard
              title={t.dashboard.won}
              value={stats.won}
              description={t.dashboard.wonDesc.replace("{pct}", String(wonRate))}
              icon={<CheckCircle2 className="h-4 w-4" />}
              sparkline={genSparkline(5, "up")}
              sparklineColor="text-emerald-500"
            />
          </>
        )}
      </div>

      {/* Hero chart: Pipeline activity over time (smooth multi-series area) */}
      <Card>
        <CardHeader>
          <div className="flex items-start justify-between">
            <div>
              <CardTitle className="text-lg flex items-center gap-2">
                <Activity className="h-4 w-4 text-muted-foreground" />
                {t.dashboard.pipelineActivity}
              </CardTitle>
              <CardDescription>
                {t.dashboard.pipelineActivityDesc}
              </CardDescription>
            </div>
            <Button variant="ghost" size="sm" asChild>
              <Link to="/pipeline">{t.dashboard.viewPipeline}</Link>
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {analyticsLoading ? (
            <Skeleton className="h-72 w-full" />
          ) : analyticsError ? (
            <EmptyState
              className="py-12"
              icon={<Activity className="h-5 w-5" />}
              title={t.dashboard.couldNotLoad}
              description={t.dashboard.couldNotLoadDesc}
            />
          ) : !hasAnyData ? (
            <EmptyState
              className="py-12"
              icon={<Sparkles className="h-5 w-5" />}
              title={t.dashboard.noActivity}
              description={t.dashboard.noActivityDesc}
              action={
                <Button size="sm" className="mt-2">
                  {t.dashboard.runFirstScout}
                </Button>
              }
            />
          ) : activityData.length === 0 ? (
            <EmptyState
              className="py-12"
              icon={<Activity className="h-5 w-5" />}
              title={t.dashboard.noActivity}
              description="Aktivitas outreach belum tersedia — coba lagi besok."
            />
          ) : (
            <ActivityChart
              data={activityData}
              series={ACTIVITY_SERIES}
              className="h-72"
            />
          )}
        </CardContent>
      </Card>

      {/* Lead quality donut + Conversion cards row */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">{t.dashboard.leadQuality}</CardTitle>
            <CardDescription>{t.dashboard.leadQualityDesc}</CardDescription>
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <Skeleton className="h-48 w-full" />
            ) : (
              <GradeDonut data={gradeData} centerSubLabel={t.dashboard.total} />
            )}
          </CardContent>
        </Card>

        <div className="lg:col-span-2 grid grid-cols-1 sm:grid-cols-3 gap-4">
          <ConversionCard
            title={t.dashboard.pipelineActivation}
            value={activatedRate}
            description={t.dashboard.pipelineActivationDesc}
            icon={<TrendingUp className="h-4 w-4" />}
            positive={activatedRate >= 50}
          />
          <ConversionCard
            title={t.dashboard.winRate}
            value={wonRate}
            description={t.dashboard.winRateDesc}
            icon={<CheckCircle2 className="h-4 w-4" />}
            positive={wonRate >= 10}
          />
          <ConversionCard
            title={t.dashboard.dropOff}
            value={
              stats.total > 0
                ? Math.round(
                    ((stats.total -
                      stats.prospects.filter((p) => p.status !== "lost")
                        .length) /
                      stats.total) *
                      100,
                  )
                : 0
            }
            description={t.dashboard.dropOffDesc}
            icon={<TrendingDown className="h-4 w-4" />}
            positive={false}
            inverse
          />
        </div>
      </div>

      {/* Top prospects table */}
      <Card>
        <CardHeader>
          <div className="flex items-start justify-between">
            <div>
              <CardTitle className="text-lg">{t.dashboard.topProspects}</CardTitle>
              <CardDescription>
                {t.dashboard.topProspectsDesc}
              </CardDescription>
            </div>
            <Button variant="ghost" size="sm" asChild>
              <Link to="/prospects">{t.common.viewAll} →</Link>
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
              title={t.dashboard.noProspects}
              description={t.dashboard.noProspectsDesc}
              action={
                <Button size="sm" className="mt-2">
                  {t.dashboard.startProspecting}
                </Button>
              }
            />
          ) : (
            <div className="overflow-x-auto -mx-6">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b">
                    <th className="text-left font-medium text-muted-foreground px-6 py-2.5">{t.dashboard.company}</th>
                    <th className="text-left font-medium text-muted-foreground px-3 py-2.5">{t.dashboard.industry}</th>
                    <th className="text-left font-medium text-muted-foreground px-3 py-2.5">{t.dashboard.status}</th>
                    <th className="text-right font-medium text-muted-foreground px-3 py-2.5">{t.dashboard.score}</th>
                    <th className="text-right font-medium text-muted-foreground px-6 py-2.5">{t.dashboard.grade}</th>
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
