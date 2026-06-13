import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";

import { cn } from "@/lib/utils";

/**
 * Badge — per UI/UX Playbook §7.4 (status pill style)
 *
 * Use for: status indicators, counts, role labels, tags
 */
const badgeVariants = cva(
  "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium " +
    "transition-colors duration-150 ease-out-expo " +
    "focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2",
  {
    variants: {
      variant: {
        default: "bg-primary text-primary-foreground",
        secondary: "bg-secondary text-secondary-foreground",
        outline: "border border-input text-foreground",
        muted: "bg-muted text-muted-foreground",
        // Status colors per playbook §8
        success: "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400",
        warning: "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400",
        danger: "bg-rose-100 text-rose-700 dark:bg-rose-900/30 dark:text-rose-400",
        info: "bg-sky-100 text-sky-700 dark:bg-sky-900/30 dark:text-sky-400",
        // Pipeline status colors (specific)
        "status-new": "bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300",
        "status-enriching": "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400",
        "status-scored": "bg-violet-100 text-violet-700 dark:bg-violet-900/30 dark:text-violet-400",
        "status-contacted": "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400",
        "status-replied": "bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400",
        "status-won": "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400",
        "status-lost": "bg-rose-100 text-rose-700 dark:bg-rose-900/30 dark:text-rose-400",
        // Grade colors
        "grade-a": "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400",
        "grade-b": "bg-sky-100 text-sky-700 dark:bg-sky-900/30 dark:text-sky-400",
        "grade-c": "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400",
        "grade-d": "bg-rose-100 text-rose-700 dark:bg-rose-900/30 dark:text-rose-400",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  },
);

export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, ...props }: BadgeProps) {
  return <div className={cn(badgeVariants({ variant }), className)} {...props} />;
}

export { Badge, badgeVariants };
