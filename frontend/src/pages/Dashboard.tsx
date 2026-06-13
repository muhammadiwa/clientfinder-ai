import { useMemo } from "react";
import { Link } from "react-router-dom";
import { TrendingUp, Users, Star, Send } from "lucide-react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import { useProspects } from "@/hooks/useProspects";
import type { Prospect, ProspectStatus } from "@/types";

interface StatCardProps {
  title: string;
  value: string | number;
  description: string;
  icon: React.ReactNode;
}

function StatCard({ title, value, description, icon }: StatCardProps) {
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardDescription className="font-medium">{title}</CardDescription>
        <div className="text-muted-foreground">{icon}</div>
      </CardHeader>
      <CardContent>
        <div className="text-3xl font-bold">{value}</div>
        <p className="text-xs text-muted-foreground mt-1">{description}</p>
      </CardContent>
    </Card>
  );
}

function StatCardSkeleton() {
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <Skeleton className="h-4 w-24" />
        <Skeleton className="h-5 w-5 rounded-full" />
      </CardHeader>
      <CardContent>
        <Skeleton className="h-8 w-16" />
        <Skeleton className="h-3 w-32 mt-2" />
      </CardContent>
    </Card>
  );
}

export function DashboardPage() {
  const { data, isLoading, isError } = useProspects({ per_page: 100 });

  const stats = useMemo(() => {
    const prospects: Prospect[] = data?.items ?? [];
    const total = data?.total ?? 0;
    const hot = prospects.filter(
      (p) => p.score_total != null && p.score_total >= 80,
    ).length;
    const contacted = prospects.filter(
      (p) => p.status === "contacted" || p.status === "replied",
    ).length;
    const won = prospects.filter((p) => p.status === "won").length;
    return { total, hot, contacted, won, prospects };
  }, [data]);

  const chartData = useMemo(() => {
    const counts: Record<ProspectStatus, number> = {
      new: 0,
      enriching: 0,
      scored: 0,
      approved: 0,
      contacted: 0,
      replied: 0,
      won: 0,
      lost: 0,
      archived: 0,
    };
    stats.prospects.forEach((p) => {
      counts[p.status] = (counts[p.status] ?? 0) + 1;
    });
    return Object.entries(counts)
      .filter(([_, v]) => v > 0)
      .map(([status, count]) => ({ status, count }));
  }, [stats.prospects]);

  return (
    <div className="space-y-6">
      <header className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Dashboard</h1>
          <p className="text-muted-foreground mt-1">
            Overview of your lead generation pipeline
          </p>
        </div>
        <Button asChild>
          <Link to="/prospects">View all prospects</Link>
        </Button>
      </header>

      {isError && (
        <Card>
          <CardContent className="py-6 text-center text-sm text-destructive">
            Could not load prospects. Check your connection or sign in again.
          </CardContent>
        </Card>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {isLoading ? (
          <>
            <StatCardSkeleton />
            <StatCardSkeleton />
            <StatCardSkeleton />
            <StatCardSkeleton />
          </>
        ) : (
          <>
            <StatCard
              title="Total Prospects"
              value={stats.total}
              description="All time"
              icon={<Users className="h-4 w-4" />}
            />
            <StatCard
              title="Hot Leads"
              value={stats.hot}
              description="Score 80+"
              icon={<Star className="h-4 w-4" />}
            />
            <StatCard
              title="Contacted"
              value={stats.contacted}
              description="Outreach sent"
              icon={<Send className="h-4 w-4" />}
            />
            <StatCard
              title="Won"
              value={stats.won}
              description="Converted to clients"
              icon={<TrendingUp className="h-4 w-4" />}
            />
          </>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>Pipeline by status</CardTitle>
            <CardDescription>
              Distribution of all discovered prospects
            </CardDescription>
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <Skeleton className="h-64 w-full" />
            ) : chartData.length === 0 ? (
              <div className="h-64 flex items-center justify-center text-sm text-muted-foreground">
                No data yet. Run a scout job in T4 to populate.
              </div>
            ) : (
              <ResponsiveContainer width="100%" height={256}>
                <BarChart data={chartData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="status" />
                  <YAxis allowDecimals={false} />
                  <Tooltip />
                  <Legend />
                  <Bar dataKey="count" fill="hsl(var(--primary))" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Recent activity</CardTitle>
            <CardDescription>Coming in T7 (Reporting Agent)</CardDescription>
          </CardHeader>
          <CardContent className="text-sm text-muted-foreground">
            Activity log will appear here once we wire the backend
            <code className="mx-1 px-1 bg-muted rounded text-xs">/activities</code>
            endpoint in T7.
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
