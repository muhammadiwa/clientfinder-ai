import {
  Area,
  AreaChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { cn } from "@/lib/utils";

export interface ActivitySeries {
  key: string;
  label: string;
  color: string; // hex (e.g. "#8b5cf6")
}

interface ActivityChartProps {
  /** Each row: { date: string, [series.key]: number } */
  data: Array<Record<string, number | string>>;
  series: ActivitySeries[];
  className?: string;
  /** Chart height in Tailwind class. Default: h-72. */
  heightClass?: string;
}

/**
 * ActivityChart — world-class multi-series area chart
 *
 * Per playbook §8.2: time-series visualization (the "grafik").
 * Replaces boring bar chart with a beautiful, smooth area chart:
 * - Multi-series (each pipeline stage = one series)
 * - Smooth monotone curves (no sharp angles)
 * - Per-series linearGradient fill (top: 50% opacity → bottom: 0%)
 * - Animated path drawing on mount
 * - Interactive tooltip (themed, popover bg, rounded, shadow)
 * - X-axis: dates (formatted as locale "short")
 * - Y-axis: count (no decimals, integer)
 * - Custom Legend with color dots
 *
 * Data is typically generated server-side in T7 (Reporting).
 * For now, deterministic Math.sin-based synthetic data gives
 * a realistic "alive" feel.
 */
export function ActivityChart({
  data,
  series,
  className,
  heightClass = "h-72",
}: ActivityChartProps) {
  const empty = data.length === 0;

  return (
    <div className={cn("w-full", heightClass, className)}>
      {empty ? (
        <div className="h-full flex items-center justify-center text-center px-4">
          <div>
            <p className="text-sm font-medium">No activity yet</p>
            <p className="text-xs text-muted-foreground mt-1">
              Activity data will appear once we have event logs (T7)
            </p>
          </div>
        </div>
      ) : (
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart
            data={data}
            margin={{ top: 5, right: 10, left: 0, bottom: 0 }}
          >
            <defs>
              {series.map((s) => (
                <linearGradient
                  key={s.key}
                  id={`activity-grad-${s.key}`}
                  x1="0"
                  y1="0"
                  x2="0"
                  y2="1"
                >
                  <stop offset="0%" stopColor={s.color} stopOpacity={0.45} />
                  <stop offset="100%" stopColor={s.color} stopOpacity={0.02} />
                </linearGradient>
              ))}
            </defs>
            <CartesianGrid
              strokeDasharray="3 3"
              stroke="hsl(var(--border))"
              strokeOpacity={0.6}
              vertical={false}
            />
            <XAxis
              dataKey="date"
              tick={{ fill: "hsl(var(--muted-foreground))", fontSize: 11 }}
              axisLine={false}
              tickLine={false}
              tickMargin={8}
            />
            <YAxis
              allowDecimals={false}
              tick={{ fill: "hsl(var(--muted-foreground))", fontSize: 11 }}
              axisLine={false}
              tickLine={false}
              width={36}
            />
            <Tooltip
              cursor={{
                stroke: "hsl(var(--muted-foreground))",
                strokeOpacity: 0.3,
                strokeDasharray: "3 3",
              }}
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
              labelStyle={{ fontWeight: 600, marginBottom: 4 }}
              itemStyle={{ padding: 0 }}
            />
            <Legend
              verticalAlign="top"
              align="right"
              iconType="circle"
              iconSize={8}
              wrapperStyle={{ fontSize: 11, paddingBottom: 8 }}
            />
            {series.map((s) => (
              <Area
                key={s.key}
                type="monotone"
                dataKey={s.key}
                stroke={s.color}
                fill={`url(#activity-grad-${s.key})`}
                strokeWidth={2}
                activeDot={{
                  r: 4,
                  stroke: "hsl(var(--card))",
                  strokeWidth: 2,
                }}
                animationDuration={900}
                animationEasing="ease-out"
              />
            ))}
          </AreaChart>
        </ResponsiveContainer>
      )}
    </div>
  );
}
