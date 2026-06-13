import { cn } from "@/lib/utils";

interface PipelineFunnelStage {
  key: string;
  label: string;
  count: number;
  dotColor: string;       // bg-{color}-500
  barColor: string;       // bg-gradient-to-r from-{c}-500 to-{c}-400
  textColor?: string;     // text-{color}-700
  emoji?: string;
}

interface PipelineFunnelProps {
  stages: PipelineFunnelStage[];
  className?: string;
}

/**
 * PipelineFunnel — world-class horizontal funnel
 *
 * Per playbook §8.2: "Pipeline by status" centerpiece chart.
 * Replaces boring bar chart with a beautiful, animated funnel.
 *
 * Each row:
 * - Status dot (color-coded per playbook §1)
 * - Stage label (font-medium)
 * - Count (text-2xl font-bold, tabular-nums)
 * - Percentage of total
 * - Horizontal bar (proportional width, gradient fill)
 * - Drop-off indicator between stages (animated ↓)
 *
 * Bars animate from 0 to width on mount via CSS keyframe.
 */
export function PipelineFunnel({ stages, className }: PipelineFunnelProps) {
  const total = stages.reduce((sum, s) => sum + s.count, 0);
  const maxCount = Math.max(...stages.map((s) => s.count), 1);

  return (
    <div className={cn("space-y-3", className)}>
      {stages.map((stage, idx) => {
        const pct = total > 0 ? (stage.count / total) * 100 : 0;
        const barWidth = (stage.count / maxCount) * 100;
        const prevCount = idx > 0 ? stages[idx - 1].count : null;
        const dropOffPct =
          prevCount !== null && prevCount > 0
            ? Math.round(((prevCount - stage.count) / prevCount) * 100)
            : null;
        const retentionPct =
          prevCount !== null && prevCount > 0
            ? Math.round((stage.count / prevCount) * 100)
            : null;
        const isLast = idx === stages.length - 1;
        const isEmpty = stage.count === 0;

        return (
          <div key={stage.key}>
            {/* Header row: dot, label, count, % */}
            <div className="flex items-center gap-3 mb-1.5">
              <span
                className={cn(
                  "h-2 w-2 rounded-full flex-shrink-0",
                  stage.dotColor,
                  isEmpty && "opacity-30",
                )}
              />
              <span
                className={cn(
                  "text-sm font-medium flex-1 min-w-0 truncate",
                  isEmpty && "text-muted-foreground",
                )}
              >
                {stage.label}
                {stage.emoji && <span className="ml-1">{stage.emoji}</span>}
              </span>
              <span
                className={cn(
                  "text-lg font-bold num tabular-nums",
                  isEmpty && "text-muted-foreground/50",
                )}
              >
                {stage.count}
              </span>
              <span
                className={cn(
                  "text-xs text-muted-foreground w-12 text-right num",
                  isEmpty && "opacity-50",
                )}
              >
                {pct.toFixed(0)}%
              </span>
            </div>

            {/* Bar */}
            <div
              className={cn(
                "relative h-2.5 bg-muted/60 rounded-full overflow-hidden",
              )}
              title={`${stage.count} (${pct.toFixed(1)}%)`}
            >
              <div
                className={cn(
                  "absolute inset-y-0 left-0 rounded-full transition-all duration-700 ease-out",
                  stage.barColor,
                  "animate-bar-grow",
                  isEmpty && "opacity-0",
                )}
                style={
                  {
                    width: `${barWidth}%`,
                    "--bar-target": `${barWidth}%`,
                  } as React.CSSProperties
                }
              />
            </div>

            {/* Drop-off / retention indicator */}
            {!isLast && (dropOffPct !== null || retentionPct !== null) && total > 0 && (
              <div
                className={cn(
                  "text-[11px] pl-5 mt-1 mb-2",
                  dropOffPct !== null && dropOffPct > 0
                    ? "text-rose-600/70"
                    : "text-emerald-600/70",
                  isEmpty && "opacity-0",
                )}
              >
                {dropOffPct !== null && dropOffPct > 0
                  ? `↓ ${dropOffPct}% drop`
                  : retentionPct === 100
                    ? "→ 100% retention"
                    : `→ ${retentionPct}% advanced`}
              </div>
            )}
          </div>
        );
      })}

      <style>{`
        @keyframes bar-grow {
          from { width: 0; }
        }
        .animate-bar-grow {
          animation: bar-grow 800ms cubic-bezier(0.16, 1, 0.3, 1);
        }
      `}</style>
    </div>
  );
}
