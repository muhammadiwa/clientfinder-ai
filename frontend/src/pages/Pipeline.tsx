import { Plus, Building2, MapPin, Inbox, Sparkles } from "lucide-react";
import { Link } from "react-router-dom";

import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { GradePill } from "@/components/ui/status-pill";
import { useProspects } from "@/hooks/useProspects";
import { t } from "@/i18n/id";
import type { Prospect, ProspectStatus } from "@/types";
import { cn } from "@/lib/utils";

const STAGES: {
  key: ProspectStatus;
  label: string;
  ring: string;
  badge: string;
}[] = [
  { key: "new", label: t.pipeline.stages.new, ring: "ring-slate-400", badge: "bg-slate-100 text-slate-700" },
  { key: "enriching", label: t.pipeline.stages.enriching, ring: "ring-blue-400", badge: "bg-blue-100 text-blue-700" },
  { key: "scored", label: t.pipeline.stages.scored, ring: "ring-violet-400", badge: "bg-violet-100 text-violet-700" },
  { key: "contacted", label: t.pipeline.stages.contacted, ring: "ring-amber-400", badge: "bg-amber-100 text-amber-700" },
  { key: "replied", label: t.pipeline.stages.replied, ring: "ring-orange-400", badge: "bg-orange-100 text-orange-700" },
  { key: "won", label: t.pipeline.stages.won, ring: "ring-emerald-400", badge: "bg-emerald-100 text-emerald-700" },
  { key: "lost", label: t.pipeline.stages.lost, ring: "ring-rose-400", badge: "bg-rose-100 text-rose-700" },
];

export function PipelinePage() {
  const { data, isLoading } = useProspects({ per_page: 100 });
  const prospects: Prospect[] = data?.items ?? [];

  // Group prospects by status
  const byStatus = STAGES.reduce<Record<string, Prospect[]>>(
    (acc, stage) => {
      acc[stage.key] = prospects.filter((p) => p.status === stage.key);
      return acc;
    },
    {},
  );

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex flex-col md:flex-row md:items-end md:justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Pipeline</h1>
          <p className="text-muted-foreground mt-2">
            {data?.total ?? 0} prospects across {STAGES.length} stages
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" asChild>
            <Link to="/prospects">
              <Sparkles className="h-4 w-4" />
              Find prospects
            </Link>
          </Button>
          <Button disabled title={t.pipeline.manualAddSoon}>
            <Plus className="h-4 w-4" />
            New prospect
          </Button>
        </div>
      </div>

      <div className="overflow-x-auto pb-4">
        <div className="flex gap-4 min-w-max">
          {STAGES.map((stage) => {
            const stageProspects = byStatus[stage.key] ?? [];
            return (
              <div key={stage.key} className="w-72 flex-shrink-0">
                <div
                  className={cn(
                    "rounded-lg bg-card ring-1 ring-inset",
                    stage.ring,
                  )}
                >
                  <div className="px-4 py-3 flex items-center justify-between border-b">
                    <div className="flex items-center gap-2">
                      <h3 className="font-semibold text-sm">{stage.label}</h3>
                      <span
                        className={cn(
                          "text-xs num px-2 py-0.5 rounded-full font-medium",
                          stage.badge,
                        )}
                      >
                        {stageProspects.length}
                      </span>
                    </div>
                    <Button
                      asChild
                      variant="ghost"
                      size="icon"
                      className="h-6 w-6 text-muted-foreground hover:text-foreground"
                      title={`Add prospect to ${stage.label}`}
                    >
                      <Link to="/prospects">
                        <Plus className="h-3.5 w-3.5" />
                      </Link>
                    </Button>
                  </div>

                  <div className="p-3 space-y-2 min-h-[200px]">
                    {isLoading ? (
                      <>
                        <Skeleton className="h-24" />
                        <Skeleton className="h-24" />
                      </>
                    ) : stageProspects.length === 0 ? (
                      <div className="h-24 rounded-lg border border-dashed border-border/50 flex flex-col items-center justify-center text-center px-2">
                        <Inbox className="h-4 w-4 text-muted-foreground/50 mb-1" />
                        <p className="text-xs text-muted-foreground">
                          No prospects in {stage.label.toLowerCase()}
                        </p>
                      </div>
                    ) : (
                      stageProspects.map((p) => (
                        <PipelineCard key={p.id} prospect={p} />
                      ))
                    )}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

function PipelineCard({ prospect }: { prospect: Prospect }) {
  return (
    <Link to="/prospects" className="block">
      <Card className="p-3 hover:shadow-md hover:-translate-y-0.5 transition-all duration-200 ease-out-expo cursor-pointer group">
        <div className="flex items-start justify-between gap-2 mb-2">
          <div className="h-8 w-8 rounded-md bg-gradient-to-br from-violet-500/20 to-indigo-500/10 border border-violet-200/50 flex items-center justify-center text-violet-700 font-semibold text-sm flex-shrink-0">
            {prospect.company_name.charAt(0).toUpperCase()}
          </div>
          {prospect.quality_grade && (
            <GradePill grade={prospect.quality_grade} />
          )}
        </div>

        <p className="font-medium text-sm leading-tight group-hover:text-primary transition-colors">
          {prospect.company_name}
        </p>

        {prospect.industry && (
          <div className="flex items-center gap-1.5 mt-1.5 text-xs text-muted-foreground">
            <Building2 className="h-3 w-3" />
            <span className="capitalize truncate">{prospect.industry}</span>
          </div>
        )}

        {prospect.location_city && (
          <div className="flex items-center gap-1.5 mt-1 text-xs text-muted-foreground">
            <MapPin className="h-3 w-3" />
            <span className="truncate">{prospect.location_city}</span>
          </div>
        )}

        {prospect.score_total != null && (
          <div className="mt-2 pt-2 border-t flex items-center justify-between">
            <span className="text-xs text-muted-foreground">Score</span>
            <span className="text-sm font-bold num text-primary">
              {prospect.score_total}
            </span>
          </div>
        )}
      </Card>
    </Link>
  );
}
