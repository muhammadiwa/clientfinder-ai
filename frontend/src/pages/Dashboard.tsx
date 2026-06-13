import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

export function DashboardPage() {
  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-3xl font-bold tracking-tight">Dashboard</h1>
        <p className="text-muted-foreground mt-1">
          Overview of your lead generation pipeline
        </p>
      </header>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {[
          { title: "Total Prospects", value: "—", desc: "All time" },
          { title: "Hot Leads", value: "—", desc: "Score 80+" },
          { title: "This Week", value: "—", desc: "New leads" },
          { title: "Reply Rate", value: "—", desc: "Last 30 days" },
        ].map((stat) => (
          <Card key={stat.title}>
            <CardHeader>
              <CardDescription>{stat.title}</CardDescription>
              <CardTitle className="text-3xl">{stat.value}</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-xs text-muted-foreground">{stat.desc}</p>
            </CardContent>
          </Card>
        ))}
      </div>

      <Card>
        <CardHeader>
          <CardTitle>T3 Group 7 placeholder</CardTitle>
          <CardDescription>
            Real charts (Recharts) and data fetching (TanStack Query) come in
            Group 7.
          </CardDescription>
        </CardHeader>
      </Card>
    </div>
  );
}
