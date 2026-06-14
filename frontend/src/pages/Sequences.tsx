import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { ListOrdered, Plus, Power, Trash2, ChevronRight } from "lucide-react";
import {
  listSequences,
  createSequence,
  updateSequence,
  deleteSequence,
  triggerDripRunner,
  getSequenceAnalytics,
  type Sequence,
  type SequenceAnalytics,
} from "@/api/outreach";
import { getT } from "@/i18n";
import { cn } from "@/lib/utils";

/**
 * Sequences — Sprint 3A frontend.
 * Lists existing sequences, lets the operator create a new one
 * (default 3-step drip: first_touch → follow_up → breakup, day
 * 0/3/7), and provides a manual "run drip" trigger.
 *
 * Step editing is intentionally minimal here — the drip runner
 * picks the channel + template automatically per prospect. The
 * sequence is mostly a schedule + max-steps.
 */
export default function SequencesPage() {
  const t = getT().sequences;
  const [sequences, setSequences] = useState<Sequence[]>([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [expanded, setExpanded] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const reload = async () => {
    setLoading(true);
    try {
      const data = await listSequences();
      setSequences(data.items);
    } catch (e: unknown) {
      setError(String((e as Error)?.message || e));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { reload(); }, []);

  const handleCreate = async () => {
    setBusy(true);
    try {
      const name = `${t.defaultName} ${sequences.length + 1}`;
      await createSequence({
        name,
        description: t.defaultDesc,
        steps: [
          { order: 0, channel: "auto", category: "first_touch", day_offset: 0 },
          { order: 1, channel: "auto", category: "follow_up", day_offset: 3 },
          { order: 2, channel: "auto", category: "breakup", day_offset: 7 },
        ],
        is_active: true,
        target_grade: null,
        target_source: null,
        target_industry: null,
        daily_send_cap: 50,
      });
      await reload();
    } catch (e: unknown) {
      setError(String((e as Error)?.message || e));
    } finally {
      setBusy(false);
    }
  };

  const handleToggle = async (s: Sequence) => {
    setBusy(true);
    try {
      await updateSequence(s.id, { is_active: !s.is_active });
      await reload();
    } catch (e: unknown) {
      setError(String((e as Error)?.message || e));
    } finally {
      setBusy(false);
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm(t.confirmDelete)) return;
    setBusy(true);
    try {
      await deleteSequence(id);
      await reload();
    } catch (e: unknown) {
      setError(String((e as Error)?.message || e));
    } finally {
      setBusy(false);
    }
  };

  const handleRunDrip = async () => {
    setBusy(true);
    try {
      await triggerDripRunner();
    } catch (e: unknown) {
      setError(String((e as Error)?.message || e));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="p-6 space-y-6 max-w-4xl mx-auto">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <ListOrdered className="h-6 w-6" />
            {t.title}
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            {t.subtitle}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={handleRunDrip}
            disabled={busy}
            data-testid="run-drip"
          >
            {t.runDrip}
          </Button>
          <Button
            onClick={handleCreate}
            disabled={busy}
            data-testid="create-sequence"
          >
            <Plus className="h-4 w-4 mr-1" />
            {t.create}
          </Button>
        </div>
      </div>

      {error && (
        <div
          data-testid="sequences-error"
          className="p-3 rounded-md border border-red-300 bg-red-50 dark:bg-red-950/30 text-sm text-red-700 dark:text-red-300"
        >
          {error}
        </div>
      )}

      {loading ? (
        <div className="space-y-3">
          <Skeleton className="h-20 w-full" />
          <Skeleton className="h-20 w-full" />
        </div>
      ) : sequences.length === 0 ? (
        <Card>
          <CardContent className="p-8 text-center text-muted-foreground">
            <ListOrdered className="h-10 w-10 mx-auto mb-2 opacity-50" />
            <p>{t.empty}</p>
            <p className="text-xs mt-1">{t.emptyDesc}</p>
          </CardContent>
        </Card>
      ) : (
        <ul className="space-y-2" data-testid="sequence-list">
          {sequences.map((s) => (
            <SequenceRow
              key={s.id}
              sequence={s}
              expanded={expanded === s.id}
              onToggleExpand={() => setExpanded(expanded === s.id ? null : s.id)}
              onToggleActive={() => handleToggle(s)}
              onDelete={() => handleDelete(s.id)}
              busy={busy}
            />
          ))}
        </ul>
      )}
    </div>
  );
}

interface SequenceRowProps {
  sequence: Sequence;
  expanded: boolean;
  onToggleExpand: () => void;
  onToggleActive: () => void;
  onDelete: () => void;
  busy: boolean;
}

function SequenceRow({
  sequence, expanded, onToggleExpand, onToggleActive, onDelete, busy,
}: SequenceRowProps) {
  const t = getT().sequences;
  return (
    <li
      data-testid="sequence-item"
      className={cn(
        "rounded-lg border border-border bg-card overflow-hidden",
        !sequence.is_active && "opacity-60",
      )}
    >
      <div className="p-3 flex items-center gap-3">
        <Button
          variant="ghost"
          size="icon"
          onClick={onToggleExpand}
          data-testid="sequence-expand"
        >
          <ChevronRight
            className={cn(
              "h-4 w-4 transition-transform",
              expanded && "rotate-90",
            )}
          />
        </Button>
        <div className="flex-1 min-w-0">
          <p className="font-medium truncate">{sequence.name}</p>
          <p className="text-xs text-muted-foreground">
            {sequence.step_count} {t.steps} · {sequence.is_active ? t.active : t.inactive}
          </p>
        </div>
        <div className="flex items-center gap-1">
          <Button
            variant="ghost"
            size="icon"
            onClick={onToggleActive}
            disabled={busy}
            data-testid="sequence-toggle"
            title={sequence.is_active ? t.deactivate : t.activate}
          >
            <Power
              className={cn(
                "h-4 w-4",
                sequence.is_active ? "text-emerald-500" : "text-zinc-400",
              )}
            />
          </Button>
          <Button
            variant="ghost"
            size="icon"
            onClick={onDelete}
            disabled={busy}
            data-testid="sequence-delete"
            title={t.delete}
          >
            <Trash2 className="h-4 w-4 text-red-500" />
          </Button>
        </div>
      </div>
      {expanded && sequence.steps && sequence.steps.length > 0 && (
        <div className="border-t bg-muted/30 px-3 py-2">
          <ol className="text-sm space-y-1.5">
            {sequence.steps.map((step, idx) => (
              <li key={idx} className="flex items-center gap-3">
                <span className="inline-flex items-center justify-center h-5 w-5 rounded-full bg-primary/10 text-xs font-semibold text-primary">
                  {idx + 1}
                </span>
                <span className="font-mono text-xs">
                  {step.category}
                </span>
                <span className="text-xs text-muted-foreground">
                  {step.channel}
                </span>
                <span className="text-xs text-muted-foreground ml-auto">
                  day +{step.day_offset ?? 0}
                </span>
              </li>
            ))}
          </ol>
          {/* Per-step analytics (Sprint 3A sub-task 3) */}
          <SequenceStats sequenceId={sequence.id} />
        </div>
      )}
    </li>
  );
}

/**
 * Per-sequence analytics widget — shown when a sequence is
 * expanded. Shows totals, today's sent count vs the cap, and
 * per-step sent/replied counts.
 */
function SequenceStats({ sequenceId }: { sequenceId: string }) {
  const t = getT().sequences;
  const [stats, setStats] = useState<SequenceAnalytics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    getSequenceAnalytics(sequenceId)
      .then((d) => { if (!cancelled) setStats(d); })
      .catch((e: unknown) => {
        if (!cancelled) setError(String((e as Error)?.message || e));
      })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [sequenceId]);

  if (loading) {
    return (
      <div
        data-testid="sequence-stats-loading"
        className="mt-3 p-2 text-xs text-muted-foreground"
      >
        {t.loadingStats}
      </div>
    );
  }
  if (error || !stats) {
    return (
      <div
        data-testid="sequence-stats-error"
        className="mt-3 p-2 text-xs text-red-500"
      >
        {error || t.statsError}
      </div>
    );
  }

  const capPct = stats.daily_send_cap > 0
    ? Math.round((stats.today_sent / stats.daily_send_cap) * 100)
    : 0;
  const capColor =
    capPct >= 90 ? "text-red-500" :
    capPct >= 60 ? "text-amber-500" : "text-emerald-500";

  return (
    <div
      data-testid="sequence-stats"
      className="mt-3 grid grid-cols-2 md:grid-cols-4 gap-2 text-xs"
    >
      {/* Cap usage */}
      <div
        data-testid="cap-usage"
        className="p-2 rounded border bg-card"
      >
        <p className="text-muted-foreground">{t.todayCap}</p>
        <p className={cn("font-semibold text-sm", capColor)}>
          {stats.today_sent} / {stats.daily_send_cap}
        </p>
        {capPct >= 60 && (
          <p className="text-[10px] mt-0.5 text-muted-foreground">
            {capPct}%
          </p>
        )}
      </div>
      {/* Totals */}
      <div
        data-testid="totals-sent"
        className="p-2 rounded border bg-card"
      >
        <p className="text-muted-foreground">{t.totalSent}</p>
        <p className="font-semibold text-sm">{stats.totals.sent}</p>
      </div>
      <div
        data-testid="totals-replied"
        className="p-2 rounded border bg-card"
      >
        <p className="text-muted-foreground">{t.totalReplied}</p>
        <p className="font-semibold text-sm">
          {stats.totals.replied}
          {stats.totals.sent > 0 && (
            <span className="text-[10px] ml-1 text-muted-foreground">
              ({Math.round(stats.totals.replied / stats.totals.sent * 100)}%)
            </span>
          )}
        </p>
      </div>
      <div
        data-testid="totals-opened"
        className="p-2 rounded border bg-card"
      >
        <p className="text-muted-foreground">{t.totalOpened}</p>
        <p className="font-semibold text-sm">{stats.totals.opened}</p>
      </div>
      {/* Per-step breakdown */}
      <div className="col-span-2 md:col-span-4 mt-1">
        <p className="text-muted-foreground mb-1">{t.perStep}</p>
        <div className="grid grid-cols-3 md:grid-cols-5 gap-1.5">
          {stats.by_step.map((s) => (
            <div
              key={s.step_index}
              data-testid={`step-stats-${s.step_index}`}
              className="p-1.5 rounded border bg-card text-center"
            >
              <p className="text-[10px] text-muted-foreground">
                {t.step} {s.step_index + 1}
              </p>
              <p className="font-semibold">{s.sent}</p>
              {s.replied > 0 && (
                <p className="text-[10px] text-emerald-600">
                  ↩ {s.replied}
                </p>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
