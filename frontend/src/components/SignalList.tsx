import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { cn } from "@/lib/utils";
import { Activity, ExternalLink } from "lucide-react";
import { getT } from "@/i18n";

export type SignalSource = "twitter" | "threads" | "social" | string;

export interface SignalItem {
  id: string;
  signal_type: string;
  source: SignalSource;
  source_url: string | null;
  raw_text: string | null;
  weight: number;       // 0..1
  detected_at: string | null;
}

interface SignalListProps {
  signals: SignalItem[];
  onReanalyze?: () => void;
  reanalyzing?: boolean;
}

/**
 * Renders the list of social signals detected for a prospect.
 * Each signal shows: kind (label), severity (weight * 100),
 * evidence text, source badge, and a deep link to the original post.
 *
 * Per brief: "butuh software" signals from public social posts
 * (Twitter + Threads). 11 kinds in the data model.
 */
export function SignalList({ signals, onReanalyze, reanalyzing }: SignalListProps) {
  const t = getT().prospectDetail.signals;

  if (signals.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-lg flex items-center gap-2">
            <Activity className="h-4 w-4 text-muted-foreground" />
            {t.section}
          </CardTitle>
          <CardDescription>
            {t.emptyDesc}
          </CardDescription>
        </CardHeader>
        <CardContent>
          <EmptyState
            icon={<Activity className="h-5 w-5" />}
            title={t.empty}
            description={t.emptyDesc}
            action={
              onReanalyze ? (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={onReanalyze}
                  disabled={reanalyzing}
                >
                  {reanalyzing ? "…" : "Run social scan"}
                </Button>
              ) : null
            }
          />
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg flex items-center gap-2">
          <Activity className="h-4 w-4 text-muted-foreground" />
          {t.section}
          <span className="ml-auto text-xs font-normal text-muted-foreground">
            {signals.length} detected
          </span>
        </CardTitle>
        <CardDescription>
          "Needs software" intent detected from public social posts
        </CardDescription>
      </CardHeader>
      <CardContent>
        <ul className="space-y-2.5" data-testid="signal-list">
          {signals.map((s) => {
            const severity = Math.round(s.weight * 100);
            const kindLabel =
              (t.kinds as Record<string, string>)[s.signal_type] ||
              s.signal_type.replace(/_/g, " ");
            const sourceLabel =
              (t.sources as Record<string, string>)[s.source] || s.source;
            return (
              <li
                key={s.id}
                data-testid="signal-item"
                className={cn(
                  "p-3 rounded-lg border border-border bg-card",
                  getSeverityBg(severity),
                )}
              >
                <div className="flex items-start gap-2.5">
                  <span
                    data-testid="signal-severity"
                    className={cn(
                      "mt-0.5 inline-flex items-center justify-center h-5 min-w-5 px-1.5 rounded text-xs font-bold uppercase",
                      getSeverityBadge(severity),
                    )}
                  >
                    {severity}
                  </span>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium leading-snug flex items-center gap-2">
                      {kindLabel}
                      <span
                        data-testid="signal-source"
                        className="inline-flex items-center rounded-full bg-muted px-2 py-0.5 text-[10px] font-medium uppercase tracking-wide text-muted-foreground"
                      >
                        {sourceLabel}
                      </span>
                    </p>
                    {s.raw_text && (
                      <p className="text-xs text-muted-foreground leading-relaxed mt-0.5 italic">
                        "{s.raw_text}"
                      </p>
                    )}
                    {s.source_url && (
                      <a
                        href={s.source_url}
                        target="_blank"
                        rel="noreferrer"
                        className="mt-1 inline-flex items-center gap-1 text-[11px] text-primary hover:underline"
                      >
                        View post <ExternalLink className="h-3 w-3" />
                      </a>
                    )}
                  </div>
                </div>
              </li>
            );
          })}
        </ul>
      </CardContent>
    </Card>
  );
}

function getSeverityBg(severity: number): string {
  if (severity >= 70) return "bg-red-50 dark:bg-red-950/30";
  if (severity >= 40) return "bg-amber-50 dark:bg-amber-950/30";
  return "bg-emerald-50 dark:bg-emerald-950/30";
}

function getSeverityBadge(severity: number): string {
  if (severity >= 70) return "bg-red-500 text-white";
  if (severity >= 40) return "bg-amber-500 text-white";
  return "bg-emerald-500 text-white";
}
