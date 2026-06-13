import { useMemo } from "react";
import { cn } from "@/lib/utils";

interface SparklineProps {
  /** Data points (numbers). 6-12 points work best. */
  data: number[];
  /** Stroke color (default: brand violet). Pass Tailwind class. */
  strokeClass?: string;
  /** Optional height in Tailwind spacing. Default: h-10. */
  className?: string;
  /** Show area fill below line. */
  showArea?: boolean;
}

/**
 * Sparkline — tiny SVG trend chart
 *
 * Used in StatCard to add visual life.
 * - Pure SVG, no library
 * - Gradient stroke (brand violet by default)
 * - Optional gradient area fill below
 * - Smooth path with subtle curve
 * - Responsive width via viewBox
 */
export function Sparkline({
  data,
  strokeClass = "stroke-violet-500",
  className,
  showArea = true,
}: SparklineProps) {
  const path = useMemo(() => {
    if (!data || data.length < 2) return { line: "", area: "" };

    const width = 100;
    const height = 30;
    const max = Math.max(...data);
    const min = Math.min(...data);
    const range = max - min || 1;

    const points = data.map((v, i) => {
      const x = (i / (data.length - 1)) * width;
      const y = height - ((v - min) / range) * (height - 4) - 2;
      return [x, y] as const;
    });

    // Smooth line (simple linear; for true smooth use Catmull-Rom)
    const line = points
      .map(([x, y], i) => `${i === 0 ? "M" : "L"}${x.toFixed(2)},${y.toFixed(2)}`)
      .join(" ");

    // Area = same line + bottom edge to close shape
    const area = `${line} L${width},${height} L0,${height} Z`;

    return { line, area };
  }, [data]);

  if (!data || data.length < 2) return null;

  return (
    <svg
      viewBox="0 0 100 30"
      preserveAspectRatio="none"
      className={cn("w-full", className)}
      aria-hidden
    >
      <defs>
        <linearGradient id="sparkline-fill" x1="0" x2="0" y1="0" y2="1">
          <stop offset="0%" stopColor="currentColor" stopOpacity="0.25" />
          <stop offset="100%" stopColor="currentColor" stopOpacity="0" />
        </linearGradient>
      </defs>
      {showArea && <path d={path.area} fill="url(#sparkline-fill)" />}
      <path
        d={path.line}
        fill="none"
        className={cn(strokeClass, "stroke-2")}
        strokeLinecap="round"
        strokeLinejoin="round"
        vectorEffect="non-scaling-stroke"
      />
    </svg>
  );
}
