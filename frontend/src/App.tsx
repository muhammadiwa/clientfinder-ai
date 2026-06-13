import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";

function ComponentsShowcase() {
  return (
    <div className="min-h-screen bg-background text-foreground">
      <div className="container mx-auto p-8 space-y-8">
        <header>
          <h1 className="text-4xl font-bold tracking-tight">
            ClientFinder AI Agent
          </h1>
          <p className="text-muted-foreground mt-2">
            T3 Group 2 — Tailwind + shadcn/ui foundation ready
          </p>
        </header>

        <section className="space-y-4">
          <h2 className="text-2xl font-semibold">Buttons</h2>
          <div className="flex flex-wrap gap-2">
            <Button>Default</Button>
            <Button variant="secondary">Secondary</Button>
            <Button variant="destructive">Destructive</Button>
            <Button variant="outline">Outline</Button>
            <Button variant="ghost">Ghost</Button>
            <Button variant="link">Link</Button>
            <Button disabled>Disabled</Button>
          </div>
        </section>

        <section className="space-y-4">
          <h2 className="text-2xl font-semibold">Inputs</h2>
          <div className="grid gap-2 max-w-sm">
            <Input placeholder="Email" type="email" />
            <Input placeholder="Password" type="password" />
            <Input placeholder="Disabled" disabled />
          </div>
        </section>

        <section className="space-y-4">
          <h2 className="text-2xl font-semibold">Card</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 max-w-2xl">
            <Card>
              <CardHeader>
                <CardTitle>Prospect Summary</CardTitle>
                <CardDescription>
                  Quick overview of your lead generation
                </CardDescription>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-muted-foreground">
                  Card components ready for use in T3 Group 7 (Dashboard).
                </p>
              </CardContent>
              <CardFooter>
                <Button variant="outline" size="sm">
                  View Details
                </Button>
              </CardFooter>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Skeleton Loader</CardTitle>
                <CardDescription>For async content</CardDescription>
              </CardHeader>
              <CardContent className="space-y-2">
                <Skeleton className="h-4 w-full" />
                <Skeleton className="h-4 w-4/5" />
                <Skeleton className="h-4 w-3/5" />
              </CardContent>
            </Card>
          </div>
        </section>

        <footer className="text-center text-sm text-muted-foreground pt-8">
          T3 Group 2 of 7 — Next: React Router + page skeleton
        </footer>
      </div>
    </div>
  );
}

export default ComponentsShowcase;
