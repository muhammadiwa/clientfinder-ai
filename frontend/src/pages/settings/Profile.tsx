import { useAuthStore } from "@/stores/auth";
import { useMe } from "@/hooks/useAuth";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Mail, ShieldCheck, User, Pencil, Clock, KeyRound } from "lucide-react";

/**
 * Settings / Profile section
 * Per playbook §8.4 — single column, max-w-2xl, section headers
 * for groups, sticky submit button at bottom (when editable).
 */
export function ProfileSection() {
  const user = useAuthStore((s) => s.user);
  const me = useMe(true);

  const displayEmail = me.data?.email ?? user?.email ?? "";
  const displayName = me.data?.full_name ?? displayEmail.split("@")[0] ?? "User";
  const displayRole = me.data?.role ?? user?.role ?? "user";
  const displayInitial = (displayEmail[0] ?? "U").toUpperCase();
  const createdAt = me.data?.created_at
    ? new Date(me.data.created_at).toLocaleDateString("id-ID", {
        day: "numeric",
        month: "long",
        year: "numeric",
      })
    : "—";

  return (
    <div className="space-y-6">
      {/* Section header */}
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Profile</h1>
        <p className="text-muted-foreground mt-1 text-sm">
          Your account information
        </p>
      </div>

      {/* Identity card */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Identity</CardTitle>
          <CardDescription>Your avatar and basic info</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-center gap-5">
            <div className="h-20 w-20 rounded-full bg-gradient-to-br from-violet-500 to-indigo-600 flex items-center justify-center text-white font-semibold text-3xl shadow-glow-sm flex-shrink-0">
              {displayInitial}
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-lg font-semibold truncate">{displayName}</p>
              <p className="text-sm text-muted-foreground truncate">
                {displayEmail}
              </p>
              <div className="mt-2 flex items-center gap-3 text-xs text-muted-foreground">
                <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-muted">
                  <ShieldCheck className="h-3 w-3" />
                  <span className="capitalize">{displayRole}</span>
                </span>
                <span className="inline-flex items-center gap-1">
                  <Clock className="h-3 w-3" />
                  Joined {createdAt}
                </span>
              </div>
            </div>
            <Button variant="outline" size="sm" disabled>
              <Pencil className="h-3.5 w-3.5" />
              Edit
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Account fields (read-only for now) */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Account</CardTitle>
          <CardDescription>
            Email, name, and other account fields
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
            <div className="space-y-2">
              <label className="text-sm font-medium flex items-center gap-2">
                <User className="h-3.5 w-3.5 text-muted-foreground" />
                Full name
              </label>
              <Input value={displayName} disabled className="h-10" />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium flex items-center gap-2">
                <Mail className="h-3.5 w-3.5 text-muted-foreground" />
                Email
              </label>
              <Input value={displayEmail} disabled className="h-10" />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium flex items-center gap-2">
                <ShieldCheck className="h-3.5 w-3.5 text-muted-foreground" />
                Role
              </label>
              <Input value={displayRole} disabled className="h-10 capitalize" />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium flex items-center gap-2">
                <KeyRound className="h-3.5 w-3.5 text-muted-foreground" />
                User ID
              </label>
              <Input
                value={me.data?.id ?? user?.id ?? ""}
                disabled
                className="h-10 font-mono text-xs"
              />
            </div>
          </div>
          <p className="text-xs text-muted-foreground mt-4">
            Profile editing will be available once multi-user support is
            added in T8.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
