import { useMemo } from "react";
import {
  PieChart,
  Pie,
  Cell,
  ResponsiveContainer,
  Tooltip,
} from "recharts";
import { cn } from "@/lib/utils";

export interface DonutSegment {
  name: string;
  value: number;
  color: string; // hex
}

interface GradeDonutProps {
  data: DonutSegment[];
  /** Text shown in the donut center. Default: total. */
  centerLabel?: string;
  centerSubLabel?: string;
  className?: string;
}

/**
 * GradeDonut — world-class donut chart with center label
 *
 * Per playbook §8.2: enhanced Lead quality donut.
 * - Center: total count + sub-label
 * - Animated: stroke-dashoffset on mount
 * - Tooltip: themed (popover bg, rounded)
 * - Legend: below with per-grade count + percentage
 */
export function GradeDonut({
  data,
  centerLabel,
  centerSubLabel = "prospects",
  className,
}: GradeDonutProps) {
  const total = useMemo(
    () => data.reduce((sum, d) => sum + d.value, 0),
    [data],
  );

  const empty = total === 0;

  if (empty) {
    return (
      <div
        className={cn(
          "h-48 flex items-center justify-center text-center",
          className,
        )}
      >
        <div>
          <p className="text-sm font-medium">No grades yet</p>
          <p className="text-xs text-muted-foreground mt-1">
            Leads will be scored automatically
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className={cn("flex flex-col items-center", className)}>
      <div className="relative">
        <ResponsiveContainer width={200} height={200}>
          <PieChart>
            <Pie
              data={data}
              cx="50%"
              cy="50%"
              innerRadius={62}
              outerRadius={88}
              paddingAngle={3}
              dataKey="value"
              stroke="hsl(var(--card))"
              strokeWidth={2}
              animationDuration={800}
              animationEasing="ease-out"
            >
              {data.map((entry) => (
                <Cell key={entry.name} fill={entry.color} />
              ))}
            </Pie>
            <Tooltip
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
              labelStyle={{ fontWeight: 600 }}
            />
          </PieChart>
        </ResponsiveContainer>
        {/* Center label */}
        <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
          <span className="text-3xl font-bold tracking-tight num">
            {centerLabel ?? total}
          </span>
          <span className="text-xs text-muted-foreground uppercase tracking-wider mt-0.5">
            {centerSubLabel}
          </span>
        </div>
      </div>
      {/* Legend */}
      <div className="flex flex-wrap gap-x-3 gap-y-1.5 mt-4 justify-center">
        {data.map((seg) => {
          const pct = (seg.value / total) * 100;
          return (
            <div
              key={seg.name}
              className="flex items-center gap-1.5 text-xs"
            >
              <span
                className="h-2 w-2 rounded-full ring-2 ring-card"
                style={{ backgroundColor: seg.color }}
              />
              <span className="font-semibold text-foreground">
                {seg.name}
              </span>
              <span className="text-muted-foreground num">
                {seg.value} · {pct.toFixed(0)}%
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
