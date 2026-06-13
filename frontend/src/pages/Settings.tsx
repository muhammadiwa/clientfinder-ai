import {
  User as UserIcon,
  Mail,
  Shield,
  Users,
  MessageSquare,
  Brain,
  Server,
  AlertTriangle,
  Sparkles,
  Check,
} from "lucide-react";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useAuthStore } from "@/stores/auth";
import { useMe } from "@/hooks/useAuth";

export function SettingsPage() {
  const user = useAuthStore((s) => s.user);
  const me = useMe(true);

  return (
    <div className="space-y-8 animate-fade-in max-w-3xl">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Settings</h1>
        <p className="text-muted-foreground mt-2">
          Account, integrations, and team management
        </p>
      </div>

      {/* Profile */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <UserIcon className="h-4 w-4" />
            Profile
          </CardTitle>
          <CardDescription>Your account information</CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="flex items-center gap-4">
            <div className="h-16 w-16 rounded-full bg-gradient-to-br from-violet-500 to-indigo-600 flex items-center justify-center text-white font-semibold text-2xl shadow-glow-sm">
              {(me.data?.email?.[0] ?? user?.email?.[0] ?? "U").toUpperCase()}
            </div>
            <div>
              <p className="font-medium">{me.data?.full_name ?? user?.email ?? "Loading..."}</p>
              <p className="text-sm text-muted-foreground">{me.data?.email ?? user?.email}</p>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <label className="text-sm font-medium flex items-center gap-2">
                <Mail className="h-3.5 w-3.5" />
                Email
              </label>
              <Input value={me.data?.email ?? ""} disabled className="h-10" />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium flex items-center gap-2">
                <Shield className="h-3.5 w-3.5" />
                Role
              </label>
              <Input value={me.data?.role ?? user?.role ?? ""} disabled className="h-10 capitalize" />
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Integrations */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Sparkles className="h-4 w-4" />
            Integrations
          </CardTitle>
          <CardDescription>
            External services connected to ClientFinder
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          {[
            {
              icon: <MessageSquare className="h-4 w-4" />,
              name: "WhatsApp (openWA)",
              desc: "Multi-number WhatsApp gateway for outreach",
              status: "connected",
              color: "emerald",
            },
            {
              icon: <Brain className="h-4 w-4" />,
              name: "LLM Providers",
              desc: "Groq (primary) + Gemini (fallback) for AI features",
              status: "connected",
              color: "violet",
            },
            {
              icon: <Server className="h-4 w-4" />,
              name: "Email (Postfix)",
              desc: "SMTP server for sending outreach emails",
              status: "coming in T6",
              color: "amber",
            },
          ].map((integration) => (
            <div
              key={integration.name}
              className="flex items-center justify-between p-4 rounded-lg border bg-muted/20 hover:bg-muted/40 transition-colors"
            >
              <div className="flex items-center gap-3">
                <div
                  className={`h-9 w-9 rounded-lg flex items-center justify-center bg-${integration.color}-100 text-${integration.color}-700`}
                >
                  {integration.icon}
                </div>
                <div>
                  <p className="font-medium text-sm">{integration.name}</p>
                  <p className="text-xs text-muted-foreground">
                    {integration.desc}
                  </p>
                </div>
              </div>
              <div>
                {integration.status === "connected" ? (
                  <span className="inline-flex items-center gap-1 text-xs font-medium text-emerald-700">
                    <Check className="h-3 w-3" />
                    Connected
                  </span>
                ) : (
                  <span className="text-xs font-medium text-amber-700">
                    {integration.status}
                  </span>
                )}
              </div>
            </div>
          ))}
        </CardContent>
      </Card>

      {/* Team (T8) */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Users className="h-4 w-4" />
            Team
          </CardTitle>
          <CardDescription>Manage team members and permissions</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="text-center py-8">
            <div className="h-12 w-12 rounded-full bg-muted flex items-center justify-center text-muted-foreground mx-auto mb-3">
              <Users className="h-5 w-5" />
            </div>
            <p className="text-sm font-medium">Multi-user support coming in T8</p>
            <p className="text-xs text-muted-foreground mt-1 max-w-xs mx-auto">
              For now, this is a single-user workspace. Team features (invite, roles, audit log) will be added in the production hardening phase.
            </p>
            <Button variant="outline" size="sm" className="mt-4" disabled>
              Invite team member
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Danger zone (placeholder) */}
      <Card className="border-rose-200">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-rose-700">
            <AlertTriangle className="h-4 w-4" />
            Danger zone
          </CardTitle>
          <CardDescription>Irreversible actions</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-between p-4 rounded-lg border border-rose-200 bg-rose-50/30">
            <div>
              <p className="font-medium text-sm">Delete account</p>
              <p className="text-xs text-muted-foreground">
                Permanently delete your account and all associated data
              </p>
            </div>
            <Button variant="outline" size="sm" disabled className="border-rose-200 text-rose-700">
              Delete account
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
