import { Users, Plus, Mail, ShieldCheck } from "lucide-react";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { useAuthStore } from "@/stores/auth";
import { useMe } from "@/hooks/useAuth";
import { useT } from "@/i18n";

/**
 * Settings / Team section
 * Single-user for now (T8 will add multi-user).
 */
export function TeamSection() {
  const t = useT();
  const user = useAuthStore((s) => s.user);
  const me = useMe(true);

  const displayEmail = me.data?.email ?? user?.email ?? "you@clientfinder.app";
  const displayName =
    me.data?.full_name ?? displayEmail.split("@")[0] ?? "You";
  const displayRole = me.data?.role ?? user?.role ?? "owner";
  const displayInitial = (displayEmail[0] ?? "U").toUpperCase();
  const joinedAt = me.data?.created_at
    ? new Date(me.data.created_at).toLocaleDateString("id-ID", {
        day: "numeric",
        month: "short",
        year: "numeric",
      })
    : "—";

  return (
    <div className="space-y-6">
      <div className="flex items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Team</h1>
          <p className="text-muted-foreground mt-1 text-sm">
            Manage team members and permissions
          </p>
        </div>
        <Button size="sm" disabled title={t.team.multiUserComing}>
          <Plus className="h-4 w-4" />
          Invite member
        </Button>
      </div>

      {/* Member list */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="text-base">Members</CardTitle>
              <CardDescription>1 of 1 (solo workspace)</CardDescription>
            </div>
            <span className="text-xs text-muted-foreground">
              Free plan · 1 seat
            </span>
          </div>
        </CardHeader>
        <CardContent className="space-y-1">
          {/* You (the owner) */}
          <div className="flex items-center gap-4 p-3 rounded-lg hover:bg-muted/30 transition-colors">
            <div className="h-10 w-10 rounded-full bg-gradient-to-br from-violet-500 to-indigo-600 flex items-center justify-center text-white font-semibold flex-shrink-0">
              {displayInitial}
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium truncate">
                {displayName}
                <span className="text-muted-foreground font-normal ml-1.5">
                  (you)
                </span>
              </p>
              <p className="text-xs text-muted-foreground truncate flex items-center gap-1">
                <Mail className="h-2.5 w-2.5" />
                {displayEmail}
              </p>
            </div>
            <div className="hidden sm:flex items-center gap-3 text-xs text-muted-foreground">
              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-violet-100 text-violet-700 dark:bg-violet-900/30 dark:text-violet-400 capitalize">
                <ShieldCheck className="h-3 w-3" />
                {displayRole}
              </span>
              <span>Joined {joinedAt}</span>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* T8 placeholder */}
      <Card>
        <CardContent className="py-10 text-center">
          <div className="h-12 w-12 rounded-full bg-muted flex items-center justify-center text-muted-foreground mx-auto mb-3">
            <Users className="h-5 w-5" />
          </div>
          <p className="text-sm font-medium">Multi-user support coming in T8</p>
          <p className="text-xs text-muted-foreground mt-1 max-w-sm mx-auto">
            For now this is a single-user workspace. Team features (invite by
            email, roles, activity log per member) ship with the production
            hardening phase.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
