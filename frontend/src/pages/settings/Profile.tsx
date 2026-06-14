import { useAuthStore } from "@/stores/auth";
import { useMe } from "@/hooks/useAuth";
import { t } from "@/i18n/id";
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
        <h1 className="text-2xl font-bold tracking-tight">{t.profile.title}</h1>
        <p className="text-muted-foreground mt-1 text-sm">
          {t.profile.subtitle}
        </p>
      </div>

      {/* Identity card */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">{t.profile.identity}</CardTitle>
          <CardDescription>{t.profile.identityDesc}</CardDescription>
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
                  {t.profile.joined.replace("{date}", createdAt)}
                </span>
              </div>
            </div>
            <Button variant="outline" size="sm" disabled>
              <Pencil className="h-3.5 w-3.5" />
              {t.profile.edit}
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Account fields (read-only for now) */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">{t.profile.account}</CardTitle>
          <CardDescription>
            {t.profile.accountDesc}
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
            <div className="space-y-2">
              <label className="text-sm font-medium flex items-center gap-2">
                <User className="h-3.5 w-3.5 text-muted-foreground" />
                {t.profile.fullName}
              </label>
              <Input value={displayName} disabled className="h-10" />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium flex items-center gap-2">
                <Mail className="h-3.5 w-3.5 text-muted-foreground" />
                {t.profile.email}
              </label>
              <Input value={displayEmail} disabled className="h-10" />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium flex items-center gap-2">
                <ShieldCheck className="h-3.5 w-3.5 text-muted-foreground" />
                {t.profile.role}
              </label>
              <Input value={displayRole} disabled className="h-10 capitalize" />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium flex items-center gap-2">
                <KeyRound className="h-3.5 w-3.5 text-muted-foreground" />
                {t.profile.userId}
              </label>
              <Input
                value={me.data?.id ?? user?.id ?? ""}
                disabled
                className="h-10 font-mono text-xs"
              />
            </div>
          </div>
          <p className="text-xs text-muted-foreground mt-4">
            {t.profile.profileEditingComing}
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
