import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

/**
 * EmptyState — world-class empty state per playbook §11
 *
 * Reusable across:
 * - Dashboard chart empty (h-72 sized)
 * - Prospects table empty (h-16 padding)
 * - Pipeline per-column empty (h-24 sized)
 * - Settings empty states
 *
 * Pass `className` to override sizing (e.g., `h-72` for tall empty).
 */
export interface EmptyStateProps {
  icon: ReactNode;
  title: string;
  description?: string;
  action?: ReactNode;
  className?: string;
  iconClassName?: string;
}

export function EmptyState({
  icon,
  title,
  description,
  action,
  className,
  iconClassName,
}: EmptyStateProps) {
  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center text-center",
        className,
      )}
    >
      <div
        className={cn(
          "h-10 w-10 rounded-full bg-muted flex items-center justify-center text-muted-foreground mb-3",
          iconClassName,
        )}
      >
        {icon}
      </div>
      <p className="text-sm font-medium">{title}</p>
      {description && (
        <p className="text-xs text-muted-foreground mt-1 max-w-xs">
          {description}
        </p>
      )}
      {action}
    </div>
  );
}
