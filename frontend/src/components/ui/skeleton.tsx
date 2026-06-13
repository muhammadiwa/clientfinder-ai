import { cn } from "@/lib/utils";

/**
 * Skeleton — per UI/UX Playbook §9
 * Animated shimmer effect for loading states
 */
function Skeleton({
  className,
  ...props
}: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn(
        "rounded-md skeleton-shimmer",
        "bg-muted/50",
        className,
      )}
      {...props}
    />
  );
}

export { Skeleton };
