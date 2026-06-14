import { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Mail, Pause, Play, StopCircle, Activity, Plus, Zap } from "lucide-react";
import {
  listEnrollments,
  pauseEnrollment,
  resumeEnrollment,
  stopEnrollment,
  enrollProspectInSequence,
  triggerDripRunner,
  listSequences,
  type EnrollmentItem,
  type Sequence,
} from "@/api/outreach";
import { getT } from "@/i18n";
import { cn } from "@/lib/utils";

interface EnrollmentPanelProps {
  prospectId: string;
  onChange?: () => void;
}

/**
 * Shows active + historical enrollments for a prospect.
 * Lets operator pause/resume/stop, and enroll the prospect in
 * a new sequence from a dropdown of available sequences.
 *
 * T9.0 / Sprint 3A — multi-channel outreach UI.
 */
export function EnrollmentPanel({ prospectId, onChange }: EnrollmentPanelProps) {
  const t = getT().prospectDetail.enrollments;
  const [enrollments, setEnrollments] = useState<EnrollmentItem[]>([]);
  const [sequences, setSequences] = useState<Sequence[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedSeq, setSelectedSeq] = useState<string>("");
  const [busy, setBusy] = useState(false);
  const [enrolling, setEnrolling] = useState(false);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const [enr, seqs] = await Promise.all([
          listEnrollments({ prospect_id: prospectId, limit: 20 }),
          listSequences(true).catch(() => ({ items: [], total: 0 })),
        ]);
        if (cancelled) return;
        setEnrollments(enr.items);
        setSequences(seqs.items);
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, [prospectId]);

  const reload = async () => {
    const enr = await listEnrollments({ prospect_id: prospectId, limit: 20 });
    setEnrollments(enr.items);
    onChange?.();
  };

  const handleEnroll = async () => {
    if (!selectedSeq) return;
    setEnrolling(true);
    try {
      await enrollProspectInSequence(prospectId, selectedSeq);
      setSelectedSeq("");
      await reload();
    } finally {
      setEnrolling(false);
    }
  };

  const handlePause = async (id: string) => {
    setBusy(true);
    try { await pauseEnrollment(id); await reload(); } finally { setBusy(false); }
  };
  const handleResume = async (id: string) => {
    setBusy(true);
    try { await resumeEnrollment(id); await reload(); } finally { setBusy(false); }
  };
  const handleStop = async (id: string) => {
    setBusy(true);
    try { await stopEnrollment(id); await reload(); } finally { setBusy(false); }
  };
  const handleDrip = async () => {
    setBusy(true);
    try { await triggerDripRunner(); await reload(); } finally { setBusy(false); }
  };

  const active = enrollments.filter(
    (e) => e.status === "active" || e.status === "paused",
  );
  const historical = enrollments.filter(
    (e) => e.status === "completed" || e.status === "stopped",
  );

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg flex items-center gap-2">
          <Activity className="h-4 w-4 text-muted-foreground" />
          {t.section}
          {active.length > 0 && (
            <span className="ml-auto text-xs font-normal text-muted-foreground">
              {active.length} {t.active}
            </span>
          )}
        </CardTitle>
        <CardDescription>{t.desc}</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Enroll-new row */}
        {sequences.length > 0 && (
          <div
            data-testid="enroll-form"
            className="flex items-center gap-2 p-3 rounded-lg border border-dashed bg-muted/30"
          >
            <select
              value={selectedSeq}
              onChange={(e) => setSelectedSeq(e.target.value)}
              data-testid="enroll-select"
              className="flex-1 h-9 rounded-md border border-input bg-background px-3 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
            >
              <option value="">{t.pickSequence}</option>
              {sequences.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name} ({s.step_count} {t.steps})
                </option>
              ))}
            </select>
            <Button
              data-testid="enroll-submit"
              size="sm"
              onClick={handleEnroll}
              disabled={!selectedSeq || enrolling}
            >
              <Plus className="h-3 w-3 mr-1" />
              {t.enroll}
            </Button>
          </div>
        )}

        {/* Active enrollments */}
        {loading ? (
          <div className="space-y-2">
            <Skeleton className="h-12 w-full" />
            <Skeleton className="h-12 w-full" />
          </div>
        ) : active.length === 0 ? (
          <p
            data-testid="enrollments-empty"
            className="text-sm text-muted-foreground italic"
          >
            {t.empty}
          </p>
        ) : (
          <ul className="space-y-2" data-testid="enrollment-list">
            {active.map((e) => (
              <EnrollmentRow
                key={e.id}
                enrollment={e}
                sequences={sequences}
                busy={busy}
                onPause={() => handlePause(e.id)}
                onResume={() => handleResume(e.id)}
                onStop={() => handleStop(e.id)}
              />
            ))}
          </ul>
        )}

        {/* Historical (collapsed) */}
        {historical.length > 0 && (
          <details className="text-xs text-muted-foreground">
            <summary className="cursor-pointer hover:text-foreground">
              {historical.length} {t.historical}
            </summary>
            <ul className="mt-2 space-y-1.5">
              {historical.map((e) => (
                <li key={e.id} className="flex items-center gap-2">
                  <span
                    className={cn(
                      "inline-block w-2 h-2 rounded-full",
                      e.status === "completed" ? "bg-emerald-500" : "bg-zinc-400",
                    )}
                  />
                  {e.status} · step {e.current_step} ·{" "}
                  {e.stopped_reason || t.endedNormally}
                </li>
              ))}
            </ul>
          </details>
        )}

        {/* Manual drip trigger (dev/operator aid) */}
        <div className="pt-2 border-t">
          <Button
            variant="ghost"
            size="sm"
            onClick={handleDrip}
            disabled={busy}
            data-testid="drip-trigger"
          >
            <Zap className="h-3 w-3 mr-1" />
            {t.runDrip}
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}

interface EnrollmentRowProps {
  enrollment: EnrollmentItem;
  sequences: Sequence[];
  busy: boolean;
  onPause: () => void;
  onResume: () => void;
  onStop: () => void;
}

function EnrollmentRow({
  enrollment, sequences, busy, onPause, onResume, onStop,
}: EnrollmentRowProps) {
  const t = getT().prospectDetail.enrollments;
  const seq = sequences.find((s) => s.id === enrollment.sequence_id);
  const seqName = seq?.name || enrollment.sequence_id.slice(0, 8);
  const isActive = enrollment.status === "active";
  const isPaused = enrollment.status === "paused";
  const nextStep = enrollment.current_step + 1;
  return (
    <li
      data-testid="enrollment-item"
      className={cn(
        "p-3 rounded-lg border border-border bg-card flex items-center gap-2",
        isPaused && "opacity-60",
      )}
    >
      <Mail className="h-4 w-4 text-muted-foreground shrink-0" />
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium leading-snug truncate">
          {seqName}
        </p>
        <p className="text-[11px] text-muted-foreground mt-0.5">
          {t.step} {enrollment.current_step} ·{" "}
          {isActive
            ? `${t.nextRun} ${formatTime(enrollment.next_action_at)}`
            : isPaused
              ? t.paused
              : t.unknown}
        </p>
      </div>
      <div className="flex items-center gap-1">
        {isActive && (
          <Button
            variant="ghost"
            size="icon"
            onClick={onPause}
            disabled={busy}
            data-testid="enrollment-pause"
            title={t.pause}
          >
            <Pause className="h-3 w-3" />
          </Button>
        )}
        {isPaused && (
          <Button
            variant="ghost"
            size="icon"
            onClick={onResume}
            disabled={busy}
            data-testid="enrollment-resume"
            title={t.resume}
          >
            <Play className="h-3 w-3" />
          </Button>
        )}
        <Button
          variant="ghost"
          size="icon"
          onClick={onStop}
          disabled={busy}
          data-testid="enrollment-stop"
          title={t.stop}
        >
          <StopCircle className="h-3 w-3" />
        </Button>
      </div>
    </li>
  );
}

function formatTime(iso: string | null): string {
  if (!iso) return "—";
  const d = new Date(iso);
  if (isNaN(d.getTime())) return "—";
  const now = Date.now();
  const diff = d.getTime() - now;
  if (Math.abs(diff) < 60_000) return "now";
  if (Math.abs(diff) < 3_600_000) {
    const m = Math.round(diff / 60_000);
    return m > 0 ? `in ${m}m` : `${-m}m ago`;
  }
  if (Math.abs(diff) < 86_400_000) {
    const h = Math.round(diff / 3_600_000);
    return h > 0 ? `in ${h}h` : `${-h}h ago`;
  }
  return d.toLocaleDateString();
}
