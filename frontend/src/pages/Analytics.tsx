import { useState } from "react";
import {
  Send,
  MessageSquare,
  Users,
  Target,
  Sparkles,
  Activity,
  BarChart3,
  Clock,
  AlertTriangle,
  Calendar,
} from "lucide-react";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import {
  getAnalyticsOverview,
  type AnalyticsOverview as AnalyticsOverviewType,
} from "@/api/analytics";
import { useQuery } from "@tanstack/react-query";
import { cn } from "@/lib/utils";
import { t } from "@/i18n/id";

const RANGE_OPTIONS = [
  { value: 7, label: t.analytics.period7d },
  { value: 30, label: t.analytics.period30d },
  { value: 90, label: t.analytics.period90d },
];

const GRADE_COLORS: Record<string, string> = {
  A: "from-emerald-500 to-emerald-400",
  B: "from-sky-500 to-sky-400",
  C: "from-amber-500 to-amber-400",
  D: "from-rose-500 to-rose-400",
};

const CHANNEL_COLORS: Record<string, string> = {
  email: "bg-violet-500",
  whatsapp: "bg-emerald-500",
  threads: "bg-sky-500",
};

// --- T7 Analytics dashboard
//
// 4 KPI categories (A. Lead Gen, B. Outreach, C. Pipeline, D. Operational)
// Hero stat cards + sparklines + tables.
//
// World-class pattern (Linear/Stripe): one lookback picker at top,
// sections flow naturally down the page, every metric has a delta hint
// or sparkline where useful.
export function AnalyticsPage() {
  const [days, setDays] = useState(30);

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["analytics", "overview", days],
    queryFn: () => getAnalyticsOverview(days),
    staleTime: 60_000,
  });

  if (isLoading || !data) return <AnalyticsSkeleton />;

  if (isError) {
    return (
      <div className="p-8 text-center">
        <AlertTriangle className="h-8 w-8 text-rose-500 mx-auto" />
        <p className="mt-2 text-sm text-muted-foreground">
          Could not load analytics. Check your connection or sign in again.
        </p>
        <Button onClick={() => refetch()} className="mt-4" size="sm">
          Try again
        </Button>
      </div>
    );
  }

  return (
    <div className="space-y-8 animate-fade-in">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-end md:justify-between gap-4">
        <div>
          <p className="text-xs uppercase tracking-wider text-muted-foreground font-semibold mb-1">
            Analytics
          </p>
          <h1 className="text-3xl font-bold tracking-tight">Performance overview</h1>
          <p className="text-muted-foreground mt-1.5 text-sm">
            {formatRange(data.range)} · semua 4 kategori KPI
          </p>
        </div>
        <RangePicker value={days} onChange={setDays} />
      </div>

      {/* Top hero — 4 most-important metrics */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <HeroMetric
          label={t.analytics.totalLeads}
          value={data.total_leads}
          icon={<Users className="h-4 w-4" />}
          tone="violet"
          sparkline={data.daily_volume.map((v) => v.baru)}
        />
        <HeroMetric
          label={t.analytics.messagesSent}
          value={data.total_messages_sent}
          icon={<Send className="h-4 w-4" />}
          tone="emerald"
          sparkline={data.daily_volume.map((v) => v.baru)}
        />
        <HeroMetric
          label={t.analytics.replyRate}
          value={computeReplyRate(data)}
          icon={<MessageSquare className="h-4 w-4" />}
          tone="sky"
          format="percent"
        />
        <HeroMetric
          label={t.analytics.winRate}
          value={data.win_rate}
          icon={<Target className="h-4 w-4" />}
          tone="amber"
          format="percent"
        />
      </div>

      {/* === A. Lead Gen === */}
      <Section
        eyebrow="A. Lead generation"
        title={t.analytics.sendApproveEngage}
        description={t.analytics.leadGenDesc}
      >
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          {/* Grade distribution (donut-like with bars) */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Grade distribution</CardTitle>
              <CardDescription>
                {data.total_leads} total leads · {data.avg_lead_score
                  ? `avg ${data.avg_lead_score.toFixed(0)}/100`
                  : "belum ada score"}
              </CardDescription>
            </CardHeader>
            <CardContent>
              <GradeBar
                A={data.grade_distribution.A}
                B={data.grade_distribution.B}
                C={data.grade_distribution.C}
                D={data.grade_distribution.D}
                unscored={data.grade_distribution.unscored}
                total={data.total_leads}
              />
            </CardContent>
          </Card>

          {/* Source quality */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Source quality</CardTitle>
              <CardDescription>
                Rata-rata score per source (lebih tinggi = lebih bagus)
              </CardDescription>
            </CardHeader>
            <CardContent>
              {data.leads_by_source.length === 0 ? (
                <EmptyMini label={t.analytics.noLeads} />
              ) : (
                <ul className="space-y-2">
                  {data.leads_by_source.map((s) => (
                    <li
                      key={s.source}
                      className="flex items-center gap-3 p-2 rounded-lg hover:bg-muted/30 transition-colors"
                    >
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium capitalize truncate">
                          {s.source.replace("_", " ")}
                        </p>
                        <p className="text-xs text-muted-foreground">
                          {s.count} leads · {s.avg_score
                            ? `avg ${s.avg_score.toFixed(0)}`
                            : "no score"}
                        </p>
                      </div>
                      <div className="text-right flex-shrink-0">
                        <p className="text-sm font-bold num tabular-nums">
                          {s.grade_a_pct.toFixed(0)}%
                        </p>
                        <p className="text-[10px] text-muted-foreground uppercase tracking-wider">
                          A-grade
                        </p>
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </CardContent>
          </Card>

          {/* Time-to-enrich */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base flex items-center gap-2">
                <Clock className="h-3.5 w-3.5" />
                Time to enrich
              </CardTitle>
              <CardDescription>
                Dari discovered sampai first analysis_completed
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                <TimeMetric
                  label="Average"
                  hours={data.time_to_enrich.avg_hours}
                />
                <TimeMetric
                  label="P50 (median)"
                  hours={data.time_to_enrich.p50_hours}
                />
                <TimeMetric
                  label="P90"
                  hours={data.time_to_enrich.p90_hours}
                />
                <p className="text-xs text-muted-foreground pt-2 border-t border-border">
                  Based on{" "}
                  <span className="font-medium num">
                    {data.time_to_enrich.n}
                  </span>{" "}
                  enriched leads
                </p>
              </div>
            </CardContent>
          </Card>
        </div>
      </Section>

      {/* === B. Outreach === */}
      <Section
        eyebrow="B. Outreach"
        title={t.analytics.sendApproveEngage}
        description={t.analytics.outreachSectionDesc}
      >
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          {/* Daily volume sparkline */}
          <Card className="lg:col-span-2">
            <CardHeader>
              <CardTitle className="text-base flex items-center gap-2">
                <BarChart3 className="h-3.5 w-3.5" />
                Daily volume
              </CardTitle>
              <CardDescription>
                Sent vs replied per day (sparkline)
              </CardDescription>
            </CardHeader>
            <CardContent>
              <DailyVolumeChart data={data.daily_volume} />
            </CardContent>
          </Card>

          {/* Per-channel breakdown */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base">By channel</CardTitle>
              <CardDescription>Per-channel performance</CardDescription>
            </CardHeader>
            <CardContent>
              {data.outreach_by_channel.every((c) => c.sent === 0 && c.replied === 0) ? (
                <EmptyMini label={t.analytics.noMessagesSent} />
              ) : (
                <ul className="space-y-3">
                  {data.outreach_by_channel.map((c) => (
                    <li
                      key={c.channel}
                      className="flex items-center gap-3 p-2.5 rounded-lg border border-border bg-card"
                    >
                      <div
                        className={cn(
                          "h-2 w-2 rounded-full",
                          CHANNEL_COLORS[c.channel] ?? "bg-muted",
                        )}
                      />
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium capitalize">
                          {c.channel}
                        </p>
                        <p className="text-xs text-muted-foreground num tabular-nums">
                          {c.sent} sent · {c.replied} replied ·{" "}
                          {c.failed} failed
                        </p>
                      </div>
                      <div className="text-right">
                        <p className="text-sm font-bold num tabular-nums">
                          {c.approval_rate.toFixed(0)}%
                        </p>
                        <p className="text-[10px] text-muted-foreground uppercase tracking-wider">
                          approval
                        </p>
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Approval funnel — horizontal bars */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Approval funnel</CardTitle>
            <CardDescription>
              Drafts → pending → approved → sent → replied
            </CardDescription>
          </CardHeader>
          <CardContent>
            <FunnelBars funnel={data.approval_funnel} />
          </CardContent>
        </Card>
      </Section>

      {/* === C. Pipeline === */}
      <Section
        eyebrow="C. Pipeline"
        title={t.analytics.stageConversion}
        description={t.analytics.pipelineSectionDesc}
      >
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          <Card className="lg:col-span-2">
            <CardHeader>
              <CardTitle className="text-base">By stage</CardTitle>
              <CardDescription>
                Count + % of all prospects
              </CardDescription>
            </CardHeader>
            <CardContent>
              {data.pipeline_by_stage.length === 0 ? (
                <EmptyMini label={t.analytics.noProspects} />
              ) : (
                <ul className="space-y-2">
                  {data.pipeline_by_stage.map((s) => (
                    <li
                      key={s.status}
                      className="flex items-center gap-3 p-2.5 rounded-lg hover:bg-muted/30 transition-colors"
                    >
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium capitalize">
                          {s.status.replace("_", " ")}
                        </p>
                        <div className="mt-1.5 h-1.5 rounded-full bg-muted overflow-hidden">
                          <div
                            className="h-full bg-gradient-to-r from-violet-500 to-violet-400 rounded-full transition-all"
                            style={{ width: `${Math.max(s.pct, 2)}%` }}
                          />
                        </div>
                      </div>
                      <div className="text-right flex-shrink-0">
                        <p className="text-sm font-bold num tabular-nums">
                          {s.count}
                        </p>
                        <p className="text-[10px] text-muted-foreground uppercase tracking-wider">
                          {s.pct}%
                        </p>
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </CardContent>
          </Card>

          <div className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Won</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-3xl font-bold tracking-tight num">
                  {data.total_won}
                </p>
                <p className="text-xs text-muted-foreground mt-1">
                  Win rate: {data.win_rate
                    ? `${(data.win_rate * 100).toFixed(1)}%`
                    : "—"}
                </p>
              </CardContent>
            </Card>
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Avg score (won)</CardTitle>
                <CardDescription>{t.analytics.avgScoreWonDesc}</CardDescription>
              </CardHeader>
              <CardContent>
                <p className="text-3xl font-bold tracking-tight num">
                  {data.avg_deal_size_proxy
                    ? data.avg_deal_size_proxy.toFixed(0)
                    : "—"}
                </p>
                <p className="text-xs text-muted-foreground mt-1">
                  Real deal size di T8
                </p>
              </CardContent>
            </Card>
          </div>
        </div>
      </Section>

      {/* === D. Operational === */}
      <Section
        eyebrow="D. Operational"
        title={t.analytics.activityLlmSuccess}
        description={t.analytics.operationalDesc}
      >
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          <Card>
            <CardHeader>
              <CardTitle className="text-base flex items-center gap-2">
                <Activity className="h-3.5 w-3.5" />
                Recent activity
              </CardTitle>
              <CardDescription>{t.analytics.recentActivity}</CardDescription>
            </CardHeader>
            <CardContent>
              {data.activity_counts.length === 0 ? (
                <EmptyMini label={t.analytics.noActivity} />
              ) : (
                <ul className="space-y-1.5 max-h-72 overflow-y-auto">
                  {data.activity_counts.slice(0, 12).map((a) => (
                    <li
                      key={a.action}
                      className="flex items-center gap-3 px-2 py-1.5 text-sm rounded hover:bg-muted/30"
                    >
                      <span className="flex-1 truncate font-mono text-xs text-muted-foreground">
                        {a.action}
                      </span>
                      <span className="num tabular-nums font-semibold">
                        {a.count}
                      </span>
                      {a.last_24h > 0 && (
                        <span className="text-[10px] text-emerald-600 font-semibold bg-emerald-50 dark:bg-emerald-950/30 px-1.5 py-0.5 rounded">
                          +{a.last_24h}
                        </span>
                      )}
                    </li>
                  ))}
                </ul>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-base flex items-center gap-2">
                <Sparkles className="h-3.5 w-3.5" />
                LLM usage
              </CardTitle>
              <CardDescription>{t.analytics.totalCalls} 1200/{t.analytics.totalCalls.toLowerCase()}</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div>
                  <p className="text-3xl font-bold tracking-tight num">
                    {data.llm_usage.total_calls}
                  </p>
                  <p className="text-xs text-muted-foreground mt-1">
                    Total calls
                  </p>
                </div>
                <div className="grid grid-cols-2 gap-3 pt-3 border-t border-border">
                  <div>
                    <p className="text-xs text-muted-foreground">Last 24h</p>
                    <p className="text-lg font-bold num tabular-nums">
                      {data.llm_usage.last_24h_calls}
                    </p>
                  </div>
                  <div>
                    <p className="text-xs text-muted-foreground">Est. tokens</p>
                    <p className="text-lg font-bold num tabular-nums">
                      {data.llm_usage.total_tokens.toLocaleString()}
                    </p>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-base">Task success rates</CardTitle>
              <CardDescription>Celery worker · scraper</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div>
                  <div className="flex items-end gap-2">
                    <p className="text-3xl font-bold tracking-tight num">
                      {data.celery_success_rate
                        ? `${data.celery_success_rate.toFixed(0)}%`
                        : "—"}
                    </p>
                  </div>
                  <p className="text-xs text-muted-foreground mt-1">
                    Celery + scraping jobs
                  </p>
                </div>
                {data.celery_success_rate !== null &&
                  data.celery_success_rate < 80 && (
                    <div className="flex items-start gap-2 p-2 rounded bg-rose-50 dark:bg-rose-950/30 border border-rose-200">
                      <AlertTriangle className="h-3.5 w-3.5 text-rose-600 flex-shrink-0 mt-0.5" />
                      <p className="text-xs text-rose-700">
                        Di bawah 80% — periksa logs Celery atau failure
                        rate di T8.
                      </p>
                    </div>
                  )}
              </div>
            </CardContent>
          </Card>
        </div>
      </Section>
    </div>
  );
}

// --- Sub-components ---

function Section({
  eyebrow,
  title,
  description,
  children,
}: {
  eyebrow: string;
  title: string;
  description: string;
  children: React.ReactNode;
}) {
  return (
    <section className="space-y-3">
      <div>
        <p className="text-[10px] uppercase tracking-wider text-violet-600 font-bold mb-1">
          {eyebrow}
        </p>
        <h2 className="text-xl font-semibold tracking-tight">{title}</h2>
        <p className="text-muted-foreground text-sm mt-0.5">{description}</p>
      </div>
      {children}
    </section>
  );
}

function HeroMetric({
  label,
  value,
  icon,
  tone,
  sparkline,
  format = "number",
}: {
  label: string;
  value: number | null;
  icon: React.ReactNode;
  tone: "violet" | "emerald" | "sky" | "amber";
  sparkline?: number[];
  format?: "number" | "percent";
}) {
  const toneClass = {
    violet: "text-violet-600 bg-violet-50 dark:bg-violet-950/30",
    emerald: "text-emerald-600 bg-emerald-50 dark:bg-emerald-950/30",
    sky: "text-sky-600 bg-sky-50 dark:bg-sky-950/30",
    amber: "text-amber-600 bg-amber-50 dark:bg-amber-950/30",
  }[tone];

  const display = (() => {
    if (value === null) return "—";
    if (format === "percent") return `${(value * 100).toFixed(0)}%`;
    return value.toLocaleString();
  })();

  return (
    <Card>
      <CardContent className="p-4">
        <div className="flex items-center justify-between mb-2">
          <span className="text-xs uppercase tracking-wider text-muted-foreground font-semibold">
            {label}
          </span>
          <div
            className={cn(
              "h-7 w-7 rounded-lg flex items-center justify-center",
              toneClass,
            )}
          >
            {icon}
          </div>
        </div>
        <p className="text-3xl font-bold tracking-tight num">{display}</p>
        {sparkline && sparkline.length > 1 && (
          <div className="mt-2 -mx-1 text-violet-500">
            <Sparkline data={sparkline} className="h-8" />
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function GradeBar({
  A,
  B,
  C,
  D,
  unscored,
  total,
}: {
  A: number;
  B: number;
  C: number;
  D: number;
  unscored: number;
  total: number;
}) {
  const segments = [
    { grade: "A", count: A, gradient: GRADE_COLORS.A, label: "A-grade" },
    { grade: "B", count: B, gradient: GRADE_COLORS.B, label: "B-grade" },
    { grade: "C", count: C, gradient: GRADE_COLORS.C, label: "C-grade" },
    { grade: "D", count: D, gradient: GRADE_COLORS.D, label: "D-grade" },
    {
      grade: "—",
      count: unscored,
      gradient: "from-muted-foreground/30 to-muted-foreground/20",
      label: "Unscored",
    },
  ];
  return (
    <div className="space-y-3">
      {/* Stacked bar */}
      <div className="h-3 rounded-full overflow-hidden flex bg-muted">
        {segments.map((s) =>
          s.count > 0 ? (
            <div
              key={s.grade}
              className={cn(
                "h-full bg-gradient-to-r",
                s.gradient,
                "transition-all",
              )}
              style={{ width: `${(s.count / total) * 100}%` }}
              title={`${s.label}: ${s.count}`}
            />
          ) : null,
        )}
      </div>
      {/* Legend */}
      <ul className="space-y-1.5">
        {segments.map((s) => (
          <li
            key={s.grade}
            className="flex items-center gap-2 text-sm"
          >
            <span
              className={cn(
                "h-2.5 w-2.5 rounded-sm bg-gradient-to-r flex-shrink-0",
                s.gradient,
              )}
            />
            <span className="font-medium">{s.grade}</span>
            <span className="text-xs text-muted-foreground">{s.label}</span>
            <span className="ml-auto num tabular-nums font-semibold">
              {s.count}
            </span>
            <span className="text-xs text-muted-foreground w-12 text-right">
              {((s.count / total) * 100).toFixed(0)}%
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}

function TimeMetric({ label, hours }: { label: string; hours: number | null }) {
  return (
    <div className="flex items-center justify-between">
      <span className="text-sm text-muted-foreground">{label}</span>
      <span className="text-sm font-semibold num tabular-nums">
        {hours === null
          ? "—"
          : hours < 1
            ? `${Math.round(hours * 60)}m`
            : hours < 48
              ? `${hours.toFixed(1)}h`
              : `${(hours / 24).toFixed(1)}d`}
      </span>
    </div>
  );
}

function FunnelBars({
  funnel,
}: {
  funnel: {
    drafts: number;
    pending_approval: number;
    approved: number;
    sent: number;
    delivered: number;
    replied: number;
    approval_rate: number;
  };
}) {
  const stages = [
    { label: "Drafts", value: funnel.drafts, color: "bg-slate-500" },
    {
      label: "Pending",
      value: funnel.pending_approval,
      color: "bg-amber-500",
    },
    {
      label: "Approved",
      value: funnel.approved,
      color: "bg-sky-500",
    },
    { label: "Sent", value: funnel.sent, color: "bg-emerald-500" },
    {
      label: "Delivered",
      value: funnel.delivered,
      color: "bg-emerald-400",
    },
    { label: "Replied", value: funnel.replied, color: "bg-violet-500" },
  ];
  const max = Math.max(...stages.map((s) => s.value), 1);
  return (
    <ul className="space-y-2.5">
      {stages.map((s) => (
        <li key={s.label} className="space-y-1">
          <div className="flex items-center justify-between text-sm">
            <span className="font-medium">{s.label}</span>
            <span className="font-bold num tabular-nums">{s.value}</span>
          </div>
          <div className="h-2.5 rounded-full bg-muted overflow-hidden">
            <div
              className={cn("h-full rounded-full transition-all", s.color)}
              style={{ width: `${(s.value / max) * 100}%` }}
            />
          </div>
        </li>
      ))}
      <li className="pt-2 mt-2 border-t border-border flex items-center justify-between text-sm">
        <span className="text-muted-foreground">Approval rate</span>
        <span className="font-bold num tabular-nums text-emerald-600">
          {funnel.approval_rate.toFixed(0)}%
        </span>
      </li>
    </ul>
  );
}

function DailyVolumeChart({
  data,
}: {
  // T8.5+++++++ (telemetry fix): consumes the
  // DailyPipeline shape from /analytics/overview.
  // We render the 'baru' (new prospects) series as
  // a simple bar chart. Uses i18n key for the label
  // (t.dashboard.new) to stay consistent with the
  // Dashboard's pipeline chart (ab6e8d4 + PR #76).
  data: { date: string; baru: number }[];
}) {
  if (data.length === 0) {
    return <EmptyMini label={t.analytics.noActivityPeriod} />;
  }
  const max = Math.max(...data.map((d) => d.baru), 1);
  return (
    <div>
      <div className="flex items-end gap-0.5 h-32">
        {data.map((d) => {
          const baruPct = (d.baru / max) * 100;
          return (
            <div
              key={d.date}
              className="flex-1 group relative"
              title={`${d.date}: ${d.baru} ${t.dashboard.new.toLowerCase()}`}
            >
              <div
                className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-violet-200 to-violet-400 dark:from-violet-900 dark:to-violet-600 rounded-t"
                style={{ height: `${baruPct}%`, minHeight: "2px" }}
              />
            </div>
          );
        })}
      </div>
      <div className="flex items-center justify-between mt-2 text-[10px] text-muted-foreground">
        <span>{data[0]?.date}</span>
        <span>{data[Math.floor(data.length / 2)]?.date}</span>
        <span>{data[data.length - 1]?.date}</span>
      </div>
      <div className="flex items-center gap-3 mt-2 text-xs">
        <span className="inline-flex items-center gap-1.5">
          <span className="h-2 w-2 rounded-sm bg-violet-400" />
          <span className="text-muted-foreground">{t.dashboard.new}</span>
        </span>
      </div>
    </div>
  );
}

function Sparkline({
  data,
  className,
}: {
  data: number[];
  className?: string;
}) {
  if (data.length < 2) return <div className={className} />;
  const max = Math.max(...data, 1);
  return (
    <svg
      viewBox={`0 0 ${data.length} 30`}
      preserveAspectRatio="none"
      className={cn("w-full text-current", className)}
    >
      <polyline
        fill="none"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
        points={data
          .map((v, i) => `${i},${30 - (v / max) * 28}`)
          .join(" ")}
      />
    </svg>
  );
}

function RangePicker({
  value,
  onChange,
}: {
  value: number;
  onChange: (v: number) => void;
}) {
  return (
    <div className="inline-flex items-center rounded-lg border border-border bg-muted/30 p-1">
      {RANGE_OPTIONS.map((o) => (
        <button
          key={o.value}
          type="button"
          onClick={() => onChange(o.value)}
          className={cn(
            "flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium rounded-md transition-colors",
            value === o.value
              ? "bg-background text-foreground shadow-sm"
              : "text-muted-foreground hover:text-foreground",
          )}
        >
          <Calendar className="h-3.5 w-3.5" />
          {o.label}
        </button>
      ))}
    </div>
  );
}

function EmptyMini({ label }: { label: string }) {
  return (
    <div className="py-6 text-center">
      <p className="text-sm text-muted-foreground">{label}</p>
    </div>
  );
}

function AnalyticsSkeleton() {
  return (
    <div className="space-y-8">
      <div className="space-y-2">
        <Skeleton className="h-3 w-24" />
        <Skeleton className="h-8 w-72" />
      </div>
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        {Array.from({ length: 4 }).map((_, i) => (
          <Skeleton key={i} className="h-24" />
        ))}
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {Array.from({ length: 3 }).map((_, i) => (
          <Skeleton key={i} className="h-48" />
        ))}
      </div>
    </div>
  );
}

// --- Helpers ---

function computeReplyRate(d: AnalyticsOverviewType): number | null {
  const sent = d.total_messages_sent;
  if (sent === 0) return null;
  let replied = 0;
  for (const c of d.outreach_by_channel) {
    replied += c.replied;
  }
  return replied / sent;
}

function formatRange(r: AnalyticsOverviewType["range"]): string {
  const start = new Date(r.start);
  const end = new Date(r.end);
  return `${start.toLocaleDateString("id-ID", {
    day: "numeric",
    month: "short",
  })} → ${end.toLocaleDateString("id-ID", {
    day: "numeric",
    month: "short",
    year: "numeric",
  })}`;
}
