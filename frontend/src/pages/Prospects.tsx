import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

export function ProspectsPage() {
  return (
    <div className="space-y-6">
      <header className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Prospects</h1>
          <p className="text-muted-foreground mt-1">
            All discovered businesses and their status
          </p>
        </div>
        <Button disabled>New search (T4)</Button>
      </header>

      <Card>
        <CardHeader>
          <CardTitle>Prospects table</CardTitle>
          <CardDescription>
            List with filters, search, and bulk actions. Wired in T3 Group 4
            (TanStack Query + API) + T4 (Scout module).
          </CardDescription>
        </CardHeader>
        <CardContent className="text-sm text-muted-foreground">
          T3 Group 4 will add data fetching. T4 will populate this with real
          leads from Google Maps, SearXNG, Twitter, Threads.
        </CardContent>
      </Card>
    </div>
  );
}
