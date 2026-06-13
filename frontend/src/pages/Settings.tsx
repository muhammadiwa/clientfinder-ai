import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";

export function SettingsPage() {
  return (
    <div className="space-y-6 max-w-2xl">
      <header>
        <h1 className="text-3xl font-bold tracking-tight">Settings</h1>
        <p className="text-muted-foreground mt-1">
          Account, integrations, and team management
        </p>
      </header>

      <Card>
        <CardHeader>
          <CardTitle>Profile</CardTitle>
          <CardDescription>Your account info (read-only for now)</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <label className="text-sm font-medium">Email</label>
            <Input value="admin@clientfinder.app" disabled />
          </div>
          <div className="space-y-2">
            <label className="text-sm font-medium">Role</label>
            <Input value="owner" disabled />
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Integrations</CardTitle>
          <CardDescription>External services (configured in T3 Group 5+)</CardDescription>
        </CardHeader>
        <CardContent className="space-y-2 text-sm text-muted-foreground">
          <p>• OpenWA (WhatsApp) — configured via .env</p>
          <p>• LLM providers (Groq, Gemini) — configured via .env</p>
          <p>• SMTP (Postfix) — added in T6</p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Team</CardTitle>
          <CardDescription>Multi-user support comes in T8</CardDescription>
        </CardHeader>
        <CardContent>
          <Button variant="outline" disabled>
            Invite team member
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
