import { cn } from "@/lib/utils";
import { Card, CardContent, CardDescription, CardHeader } from "@/components/ui/card";
import type { ReactNode } from "react";

/**
 * StatCard — per UI/UX Playbook §7.3
 * - Gradient left border (4px wide)
 * - Icon in muted circle
 * - Big number (text-3xl font-bold)
 * - Optional delta indicator
 */
export interface StatCardProps {
  title: string;
  value: string | number;
  description?: string;
  icon: ReactNode;
  delta?: {
    value: number;
    label?: string;
    positive?: boolean;
  };
  className?: string;
}

export function StatCard({
  title,
  value,
  description,
  icon,
  delta,
  className,
}: StatCardProps) {
  return (
    <Card className={cn("relative overflow-hidden", className)}>
      {/* Gradient left border */}
      <div className="absolute inset-y-0 left-0 w-1 bg-gradient-to-b from-violet-500 via-indigo-500 to-violet-500" />

      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardDescription className="font-medium text-xs uppercase tracking-wide">
          {title}
        </CardDescription>
        <div className="h-9 w-9 rounded-lg bg-muted flex items-center justify-center text-muted-foreground">
          {icon}
        </div>
      </CardHeader>
      <CardContent>
        <div className="text-3xl font-bold tracking-tight num">{value}</div>
        {(delta || description) && (
          <div className="flex items-center gap-1.5 text-xs mt-2">
            {delta && (
              <span
                className={cn(
                  "inline-flex items-center gap-0.5 font-medium",
                  delta.positive ? "text-emerald-600" : "text-rose-600",
                )}
              >
                <span aria-hidden>{delta.positive ? "▲" : "▼"}</span>
                {Math.abs(delta.value)}%
              </span>
            )}
            {delta && description && (
              <span className="text-muted-foreground/50">·</span>
            )}
            {description && (
              <span className="text-muted-foreground">{description}</span>
            )}
            {delta?.label && !description && (
              <span className="text-muted-foreground">{delta.label}</span>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
