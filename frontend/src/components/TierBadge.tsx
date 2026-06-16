import { Building2, Building, Castle, HelpCircle } from "lucide-react";
import type { Tier } from "@/api/prospects";
import { cn } from "@/lib/utils";
import { getT } from "@/i18n";

interface TierBadgeProps {
  tier: Tier | null | undefined;
  confidence?: number;
  className?: string;
}

/**
 * TierBadge — Sprint 3B frontend.
 *
 * Color-coded badge for SMB / Mid / Enterprise tier.
 * Per the brief's UMKM-first design (Indonesia context),
 * SMB is the most desirable tier (most likely to need our
 * help); Enterprise is the least (often have internal IT).
 *
 * The badge is small, fits next to the grade pill, and shows
 * the confidence as a subscript when confidence < 0.7.
 */
export function TierBadge({ tier, confidence, className }: TierBadgeProps) {
  const t = getT().prospectDetail.tier;
  if (!tier || tier === "unknown") {
    return (
      <span
        data-testid="tier-badge"
        data-tier="unknown"
        className={cn(
          "inline-flex items-center gap-1 rounded-full bg-zinc-100 text-zinc-600 px-2 py-0.5 text-[10px] font-medium uppercase tracking-wide dark:bg-zinc-800 dark:text-zinc-300",
          className,
        )}
      >
        <HelpCircle className="h-3 w-3" />
        {t.unknown}
      </span>
    );
  }

  const config = {
    smb: {
      icon: Building,
      color: "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300",
      label: t.smb,
    },
    mid: {
      icon: Building2,
      color: "bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300",
      label: t.mid,
    },
    enterprise: {
      icon: Castle,
      color: "bg-violet-100 text-violet-700 dark:bg-violet-900/40 dark:text-violet-300",
      label: t.enterprise,
    },
    unknown: {
      icon: HelpCircle,
      color: "bg-zinc-100 text-zinc-600 dark:bg-zinc-800 dark:text-zinc-300",
      label: t.unknown,
    },
  }[tier];

  const Icon = config.icon;
  return (
    <span
      data-testid="tier-badge"
      data-tier={tier}
      title={confidence != null ? `${t.confidence}: ${Math.round(confidence * 100)}%` : undefined}
      className={cn(
        "inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-medium uppercase tracking-wide",
        config.color,
        className,
      )}
    >
      <Icon className="h-3 w-3" />
      {config.label}
      {confidence != null && confidence < 0.7 && (
        <span className="text-[9px] opacity-60">
          {Math.round(confidence * 100)}%
        </span>
      )}
    </span>
  );
}
