import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

const STAGES = [
  { key: "new", label: "New", color: "bg-slate-200" },
  { key: "enriching", label: "Enriching", color: "bg-blue-200" },
  { key: "scored", label: "Scored", color: "bg-purple-200" },
  { key: "contacted", label: "Contacted", color: "bg-yellow-200" },
  { key: "replied", label: "Replied", color: "bg-orange-200" },
  { key: "won", label: "Won", color: "bg-green-200" },
  { key: "lost", label: "Lost", color: "bg-red-200" },
];

export function PipelinePage() {
  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-3xl font-bold tracking-tight">Pipeline</h1>
        <p className="text-muted-foreground mt-1">
          Kanban view of prospects by stage
        </p>
      </header>

      <div className="grid grid-cols-7 gap-3">
        {STAGES.map((stage) => (
          <Card key={stage.key}>
            <CardHeader className="pb-3">
              <div className="flex items-center gap-2">
                <div className={`w-2 h-2 rounded-full ${stage.color}`} />
                <CardTitle className="text-sm">{stage.label}</CardTitle>
              </div>
              <CardDescription className="text-xs">0 prospects</CardDescription>
            </CardHeader>
            <CardContent className="text-xs text-muted-foreground">
              Drag &amp; drop in T3 Group 7
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
