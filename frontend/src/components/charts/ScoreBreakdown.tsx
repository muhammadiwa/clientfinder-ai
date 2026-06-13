import { useMemo } from "react";
import { cn } from "@/lib/utils";

export interface ScoreFactor {
  key: string;
  label: string;
  value: number; // 0-100
  description?: string;
}

interface ScoreBreakdownChartProps {
  factors: ScoreFactor[];
  total: number;
  grade: string;
  className?: string;
}

/**
 * ScoreBreakdown — 5-factor horizontal bar chart with grade hero.
 *
 * Per playbook §7.3 + §8.2 (component pattern). Used in prospect
 * detail page to visualize the lead_score breakdown.
 *
 * Design:
 *  - Big grade badge (A/B/C/D) on the left
 *  - Total score (0-100) under the grade
 *  - 5 horizontal bars on the right, each labeled
 *  - Each bar: gradient fill + value at the end
 *  - Color-coded by score range (red <40, amber 40-59, sky 60-79, emerald 80+)
 */
export function ScoreBreakdownChart({
  factors,
  total,
  grade,
  className,
}: ScoreBreakdownChartProps) {
  const gradeMeta = useMemo(() => getGradeMeta(grade), [grade]);
  const totalColor = useMemo(
    () => getScoreColor(total),
    [total],
  );

  return (
    <div
      className={cn(
        "grid grid-cols-1 md:grid-cols-[200px_1fr] gap-6",
        className,
      )}
    >
      {/* Grade hero (left) */}
      <div className="flex flex-col items-center justify-center text-center p-6 rounded-xl border border-border bg-card">
        <div className="text-xs uppercase tracking-wider text-muted-foreground font-semibold">
          Grade
        </div>
        <div
          className={cn(
            "text-7xl font-bold tracking-tight my-2",
            gradeMeta.textClass,
          )}
        >
          {grade}
        </div>
        <div className="text-xs text-muted-foreground mb-3">
          {gradeMeta.label}
        </div>
        <div className="w-full border-t border-border pt-3 mt-1">
          <div className="text-xs uppercase tracking-wider text-muted-foreground font-semibold mb-1">
            Total
          </div>
          <div
            className={cn(
              "text-3xl font-bold tracking-tight num",
              totalColor.textClass,
            )}
          >
            {Math.round(total)}
            <span className="text-base text-muted-foreground font-normal">
              /100
            </span>
          </div>
        </div>
      </div>

      {/* Factor bars (right) */}
      <div className="space-y-3">
        {factors.map((factor) => {
          const color = getScoreColor(factor.value);
          const pct = Math.max(0, Math.min(100, factor.value));
          return (
            <div key={factor.key} className="space-y-1.5">
              <div className="flex items-center justify-between text-sm">
                <div className="flex items-center gap-2 min-w-0">
                  <span className="font-medium truncate">
                    {factor.label}
                  </span>
                  {factor.description && (
                    <span className="text-xs text-muted-foreground truncate hidden sm:inline">
                      {factor.description}
                    </span>
                  )}
                </div>
                <span
                  className={cn(
                    "text-sm font-bold num tabular-nums ml-2",
                    color.textClass,
                  )}
                >
                  {Math.round(factor.value)}
                </span>
              </div>
              <div className="relative h-2 bg-muted/60 rounded-full overflow-hidden">
                <div
                  className={cn(
                    "absolute inset-y-0 left-0 rounded-full transition-all duration-700 ease-out-expo",
                    color.barClass,
                  )}
                  style={{ width: `${pct}%` }}
                />
                {/* Tick marks at 50, 80 */}
                <div
                  className="absolute inset-y-0 w-px bg-border/50"
                  style={{ left: "50%" }}
                  aria-hidden
                />
                <div
                  className="absolute inset-y-0 w-px bg-border/50"
                  style={{ left: "80%" }}
                  aria-hidden
                />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// --- Helpers ---

function getScoreColor(score: number): {
  textClass: string;
  barClass: string;
} {
  if (score >= 80)
    return {
      textClass: "text-emerald-600",
      barClass: "bg-gradient-to-r from-emerald-500 to-emerald-400",
    };
  if (score >= 60)
    return {
      textClass: "text-sky-600",
      barClass: "bg-gradient-to-r from-sky-500 to-sky-400",
    };
  if (score >= 40)
    return {
      textClass: "text-amber-600",
      barClass: "bg-gradient-to-r from-amber-500 to-amber-400",
    };
  return {
    textClass: "text-rose-600",
    barClass: "bg-gradient-to-r from-rose-500 to-rose-400",
  };
}

function getGradeMeta(grade: string): {
  label: string;
  textClass: string;
} {
  switch (grade) {
    case "A":
      return { label: "Hot lead — pursue", textClass: "text-emerald-600" };
    case "B":
      return { label: "Warm lead", textClass: "text-sky-600" };
    case "C":
      return { label: "Possible", textClass: "text-amber-600" };
    case "D":
      return { label: "Cold / Low priority", textClass: "text-rose-600" };
    default:
      return { label: "Unscored", textClass: "text-muted-foreground" };
  }
}
