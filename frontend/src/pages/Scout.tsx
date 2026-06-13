import {
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import {
  Search,
  MapPin,
  Sparkles,
  RotateCcw,
  Trash2,
  Loader2,
  CheckCircle2,
  XCircle,
  Clock,
  Globe,
  Twitter,
  MessagesSquare,
  Sparkles as SparklesIcon,
  ArrowRight,
} from "lucide-react";
import { toast } from "react-hot-toast";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/ui/empty-state";
import {
  createScrapingJob,
  deleteScrapingJob,
  listScrapingJobs,
  listScrapingPresets,
  retryScrapingJob,
  type ScrapingJobCreate,
  type ScrapingPreset,
} from "@/api/scouting";
import { useProspects } from "@/hooks/useProspects";
import type { ScrapingJob, ScrapingSource } from "@/types";
import { cn } from "@/lib/utils";

interface SourceOption {
  id: ScrapingSource;
  label: string;
  icon: React.ReactNode;
  available: boolean;
  description: string;
}

const SOURCES: SourceOption[] = [
  {
    id: "google",
    label: "Google Search",
    icon: <Globe className="h-4 w-4" />,
    available: true,
    description: "SearXNG meta-search (Google + DuckDuckGo + Bing + Brave)",
  },
  {
    id: "maps",
    label: "Google Maps",
    icon: <MapPin className="h-4 w-4" />,
    available: true,
    description: "Playwright headless Chromium — businesses, addresses, phones",
  },
  {
    id: "twitter",
    label: "Twitter / X",
    icon: <Twitter className="h-4 w-4" />,
    available: false,
    description: "Coming in T4.5 — needs logged-in session cookies",
  },
  {
    id: "threads",
    label: "Threads",
    icon: <MessagesSquare className="h-4 w-4" />,
    available: false,
    description: "Coming in T4.5 — needs logged-in session cookies",
  },
];

const STATUS_BADGE: Record<
  string,
  { label: string; className: string }
> = {
  pending: {
    label: "Pending",
    className:
      "bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300",
  },
  running: {
    label: "Running",
    className:
      "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400",
  },
  completed: {
    label: "Completed",
    className:
      "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400",
  },
  failed: {
    label: "Failed",
    className:
      "bg-rose-100 text-rose-700 dark:bg-rose-900/30 dark:text-rose-400",
  },
};

const POLL_INTERVAL_MS = 3_000;

export function ScoutPage() {
  // Form state
  const [source, setSource] = useState<ScrapingSource>("google");
  const [keywords, setKeywords] = useState("");
  const [location, setLocation] = useState("");
  const [maxResults, setMaxResults] = useState(20);
  const [submitting, setSubmitting] = useState(false);

  // Data
  const [jobs, setJobs] = useState<ScrapingJob[]>([]);
  const [jobsLoading, setJobsLoading] = useState(true);
  const [presets, setPresets] = useState<ScrapingPreset[]>([]);
  const [presetsLoading, setPresetsLoading] = useState(true);
  const [reloadKey, setReloadKey] = useState(0);

  // Recent discoveries (use existing prospects endpoint, filtered by source != 'manual')
  const {
    data: recentProspectsData,
    isLoading: recentLoading,
  } = useProspects({ per_page: 8 });

  // Poll for job status when there are running/pending jobs
  const hasActiveJobs = useMemo(
    () =>
      jobs.some(
        (j) => j.status === "pending" || j.status === "running",
      ),
    [jobs],
  );
  const pollRef = useRef<number | null>(null);
  useEffect(() => {
    if (hasActiveJobs) {
      pollRef.current = window.setInterval(() => {
        setReloadKey((k) => k + 1);
      }, POLL_INTERVAL_MS);
    }
    return () => {
      if (pollRef.current) window.clearInterval(pollRef.current);
    };
  }, [hasActiveJobs]);

  // Fetch jobs (re-runs on reloadKey)
  useEffect(() => {
    let cancelled = false;
    setJobsLoading(true);
    listScrapingJobs(1, 20)
      .then((data) => {
        if (!cancelled) setJobs(data.items);
      })
      .catch(() => {
        if (!cancelled) setJobs([]);
      })
      .finally(() => {
        if (!cancelled) setJobsLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [reloadKey]);

  // Fetch presets once
  useEffect(() => {
    let cancelled = false;
    setPresetsLoading(true);
    listScrapingPresets()
      .then((p) => {
        if (!cancelled) setPresets(p);
      })
      .catch(() => {
        if (!cancelled) setPresets([]);
      })
      .finally(() => {
        if (!cancelled) setPresetsLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const recentProspects = recentProspectsData?.items ?? [];

  const handlePreset = (p: ScrapingPreset) => {
    setSource(p.source);
    setKeywords(p.query.keywords);
    setLocation(p.query.location ?? "");
    setMaxResults(p.query.max_results ?? 20);
    // Smooth scroll to the form
    document
      .getElementById("scout-form-card")
      ?.scrollIntoView({ behavior: "smooth", block: "start" });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!keywords.trim()) {
      toast.error("Keywords required");
      return;
    }
    const sourceOpt = SOURCES.find((s) => s.id === source);
    if (!sourceOpt?.available) {
      toast.error(`${sourceOpt?.label ?? source} coming soon`);
      return;
    }
    setSubmitting(true);
    const payload: ScrapingJobCreate = {
      source,
      keywords: keywords.trim(),
      location: location.trim() || undefined,
      max_results: maxResults,
    };
    try {
      await createScrapingJob(payload);
      toast.success(
        `Job started — ${sourceOpt.label} is searching for prospects…`,
      );
      setKeywords("");
      setLocation("");
      setReloadKey((k) => k + 1);
    } catch (e) {
      toast.error(
        e instanceof Error ? e.message : "Failed to create job",
      );
    } finally {
      setSubmitting(false);
    }
  };

  const handleRetry = async (id: string) => {
    try {
      await retryScrapingJob(id);
      toast.success("Job re-queued");
      setReloadKey((k) => k + 1);
    } catch {
      toast.error("Could not retry job");
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm("Delete this job? (Prospects already added are kept.)")) return;
    try {
      await deleteScrapingJob(id);
      toast.success("Job deleted");
      setReloadKey((k) => k + 1);
    } catch {
      toast.error("Could not delete job");
    }
  };

  return (
    <div className="space-y-8 animate-fade-in">
      {/* Hero header */}
      <div className="flex flex-col md:flex-row md:items-end md:justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Scout</h1>
          <p className="text-muted-foreground mt-2 max-w-2xl">
            Discover Indonesian UMKM that need software services. AI
            scrapes Google, Maps, and more — you review the results.
          </p>
        </div>
      </div>

      {/* Presets (quick start) */}
      <div>
        <div className="flex items-center gap-2 mb-3">
          <SparklesIcon className="h-4 w-4 text-muted-foreground" />
          <h2 className="text-sm font-semibold uppercase tracking-wider text-muted-foreground">
            Quick-start presets
          </h2>
        </div>
        {presetsLoading ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
            <Skeleton className="h-20" />
            <Skeleton className="h-20" />
            <Skeleton className="h-20" />
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
            {presets.map((p) => (
              <button
                key={p.id}
                type="button"
                onClick={() => handlePreset(p)}
                className={cn(
                  "text-left p-4 rounded-lg border border-border bg-card",
                  "hover:border-violet-300 hover:bg-accent/30 transition-colors",
                )}
              >
                <p className="text-sm font-medium">{p.name}</p>
                <p className="text-xs text-muted-foreground mt-0.5">
                  {SOURCES.find((s) => s.id === p.source)?.label ?? p.source} ·{" "}
                  "{p.query.keywords}"{p.query.location ? `, ${p.query.location}` : ""}
                </p>
              </button>
            ))}
          </div>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Create job form */}
        <Card id="scout-form-card" className="lg:col-span-2">
          <CardHeader>
            <CardTitle className="text-lg flex items-center gap-2">
              <Search className="h-4 w-4" />
              New scout job
            </CardTitle>
            <CardDescription>
              Pick a source, write your query, hit start
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-5">
              {/* Source selector */}
              <div>
                <label className="text-sm font-medium">Source</label>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-2 mt-2">
                  {SOURCES.map((s) => {
                    const isActive = source === s.id;
                    return (
                      <button
                        key={s.id}
                        type="button"
                        disabled={!s.available}
                        onClick={() => setSource(s.id)}
                        className={cn(
                          "flex flex-col items-start gap-1.5 p-3 rounded-lg border text-left transition-all duration-150",
                          isActive
                            ? "border-violet-500 bg-violet-50 dark:bg-violet-950/30 ring-1 ring-violet-500"
                            : "border-border bg-background hover:border-violet-300",
                          !s.available && "opacity-50 cursor-not-allowed",
                        )}
                        title={s.available ? s.description : "Coming soon"}
                      >
                        <div className="flex items-center gap-2">
                          {s.icon}
                          <span className="text-sm font-medium">{s.label}</span>
                        </div>
                        <p className="text-[11px] text-muted-foreground line-clamp-2">
                          {s.description}
                        </p>
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* Keywords */}
              <div className="space-y-2">
                <label htmlFor="keywords" className="text-sm font-medium">
                  Keywords
                </label>
                <Input
                  id="keywords"
                  placeholder={
                    source === "maps"
                      ? "restoran, kafe, klinik gigi…"
                      : "klinik gigi jakarta, website UMKM…"
                  }
                  value={keywords}
                  onChange={(e) => setKeywords(e.target.value)}
                  required
                  disabled={submitting}
                  className="h-10"
                />
              </div>

              {/* Location (optional, especially for maps) */}
              <div className="space-y-2">
                <label htmlFor="location" className="text-sm font-medium">
                  Location{" "}
                  <span className="text-xs text-muted-foreground font-normal">
                    (optional)
                  </span>
                </label>
                <Input
                  id="location"
                  placeholder="Jakarta, Bandung, Jabodetabek…"
                  value={location}
                  onChange={(e) => setLocation(e.target.value)}
                  disabled={submitting}
                  className="h-10"
                />
              </div>

              {/* Max results */}
              <div className="space-y-2">
                <label htmlFor="max" className="text-sm font-medium flex justify-between">
                  <span>Max results</span>
                  <span className="text-muted-foreground num text-xs">
                    {maxResults}
                  </span>
                </label>
                <input
                  id="max"
                  type="range"
                  min={5}
                  max={50}
                  step={5}
                  value={maxResults}
                  onChange={(e) => setMaxResults(Number(e.target.value))}
                  className="w-full accent-violet-600"
                />
              </div>

              <Button
                type="submit"
                className="w-full"
                size="lg"
                disabled={submitting}
              >
                {submitting ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" />
                    Starting…
                  </>
                ) : (
                  <>
                    <Sparkles className="h-4 w-4" />
                    Start scout job
                    <ArrowRight className="h-4 w-4" />
                  </>
                )}
              </Button>
            </form>
          </CardContent>
        </Card>

        {/* Active jobs */}
        <Card>
          <CardHeader>
            <CardTitle className="text-lg flex items-center gap-2">
              <Clock className="h-4 w-4" />
              Active jobs
            </CardTitle>
            <CardDescription>
              {hasActiveJobs
                ? "Polling every 3s while jobs run…"
                : "Idle — start a job to see live updates"}
            </CardDescription>
          </CardHeader>
          <CardContent>
            {jobsLoading ? (
              <div className="space-y-2">
                {Array.from({ length: 3 }).map((_, i) => (
                  <Skeleton key={i} className="h-12" />
                ))}
              </div>
            ) : jobs.length === 0 ? (
              <EmptyState
                className="py-6"
                icon={<Sparkles className="h-5 w-5" />}
                title="No jobs yet"
                description="Start your first scout job to see activity here"
              />
            ) : (
              <div className="space-y-2 max-h-[480px] overflow-y-auto -mx-1 px-1">
                {jobs.slice(0, 10).map((job) => (
                  <JobRow
                    key={job.id}
                    job={job}
                    onRetry={handleRetry}
                    onDelete={handleDelete}
                  />
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Recent discoveries */}
      <Card>
        <CardHeader>
          <div className="flex items-start justify-between">
            <div>
              <CardTitle className="text-lg flex items-center gap-2">
                <CheckCircle2 className="h-4 w-4" />
                Recent discoveries
              </CardTitle>
              <CardDescription>
                Latest prospects from scout jobs (also visible in Prospects)
              </CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {recentLoading ? (
            <div className="space-y-2">
              {Array.from({ length: 3 }).map((_, i) => (
                <Skeleton key={i} className="h-12" />
              ))}
            </div>
          ) : recentProspects.length === 0 ? (
            <EmptyState
              className="py-8"
              icon={<Globe className="h-5 w-5" />}
              title="No prospects yet"
              description="Start a scout job and new prospects will appear here automatically"
            />
          ) : (
            <div className="overflow-x-auto -mx-6">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b">
                    <th className="text-left font-medium text-muted-foreground px-6 py-2.5">Company</th>
                    <th className="text-left font-medium text-muted-foreground px-3 py-2.5">Source</th>
                    <th className="text-left font-medium text-muted-foreground px-3 py-2.5">Location</th>
                    <th className="text-right font-medium text-muted-foreground px-6 py-2.5">When</th>
                  </tr>
                </thead>
                <tbody>
                  {recentProspects.map((p) => (
                    <tr
                      key={p.id}
                      className="border-b last:border-0 hover:bg-muted/30 transition-colors"
                    >
                      <td className="px-6 py-3 font-medium">{p.company_name}</td>
                      <td className="px-3 py-3 text-muted-foreground capitalize">
                        {p.source}
                      </td>
                      <td className="px-3 py-3 text-muted-foreground">
                        {p.location_city ?? "—"}
                      </td>
                      <td className="px-6 py-3 text-right text-xs text-muted-foreground num">
                        {formatRelative(p.discovered_at)}
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

interface JobRowProps {
  job: ScrapingJob;
  onRetry: (id: string) => void;
  onDelete: (id: string) => void;
}

function JobRow({ job, onRetry, onDelete }: JobRowProps) {
  const status = STATUS_BADGE[job.status] ?? STATUS_BADGE.pending;
  const statusIcon = (() => {
    switch (job.status) {
      case "completed":
        return <CheckCircle2 className="h-3.5 w-3.5" />;
      case "failed":
        return <XCircle className="h-3.5 w-3.5" />;
      case "running":
        return <Loader2 className="h-3.5 w-3.5 animate-spin" />;
      default:
        return <Clock className="h-3.5 w-3.5" />;
    }
  })();

  return (
    <div className="p-3 rounded-lg border border-border bg-card/50 hover:bg-card transition-colors">
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0 flex-1">
          <p className="text-sm font-medium truncate">
            {job.query.keywords}
            {job.query.location && (
              <span className="text-muted-foreground font-normal">
                {" "}· {job.query.location}
              </span>
            )}
          </p>
          <div className="flex items-center gap-2 mt-1.5">
            <span
              className={cn(
                "inline-flex items-center gap-1 text-xs font-medium px-1.5 py-0.5 rounded-full",
                status.className,
              )}
            >
              {statusIcon}
              {status.label}
            </span>
            <span className="text-xs text-muted-foreground capitalize">
              {job.source}
            </span>
            {job.status === "completed" && (
              <span className="text-xs text-emerald-600 font-medium num">
                +{job.prospects_found} prospects
              </span>
            )}
          </div>
          {job.error_message && (
            <p className="text-xs text-rose-600 mt-1 line-clamp-2">
              {job.error_message}
            </p>
          )}
        </div>
        <div className="flex items-center gap-0.5 flex-shrink-0">
          {(job.status === "failed" || job.status === "completed") && (
            <Button
              variant="ghost"
              size="icon"
              className="h-7 w-7"
              onClick={() => onRetry(job.id)}
              title="Retry"
            >
              <RotateCcw className="h-3.5 w-3.5" />
            </Button>
          )}
          <Button
            variant="ghost"
            size="icon"
            className="h-7 w-7"
            onClick={() => onDelete(job.id)}
            title="Delete"
          >
            <Trash2 className="h-3.5 w-3.5" />
          </Button>
        </div>
      </div>
    </div>
  );
}

function formatRelative(iso: string): string {
  const then = new Date(iso).getTime();
  if (Number.isNaN(then)) return "—";
  const diff = Date.now() - then;
  const sec = Math.floor(diff / 1000);
  if (sec < 60) return `${sec}s ago`;
  const min = Math.floor(sec / 60);
  if (min < 60) return `${min}m ago`;
  const hr = Math.floor(min / 60);
  if (hr < 24) return `${hr}h ago`;
  const days = Math.floor(hr / 24);
  return `${days}d ago`;
}
