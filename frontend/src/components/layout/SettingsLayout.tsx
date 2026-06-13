import { NavLink, Outlet } from "react-router-dom";
import {
  User,
  Sparkles,
  Users,
  AlertTriangle,
  ShieldCheck,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useAuthStore } from "@/stores/auth";
import { useMe } from "@/hooks/useAuth";

interface Section {
  to: string;
  label: string;
  icon: React.ReactNode;
  danger?: boolean;
}

const SECTIONS: Section[] = [
  { to: "/settings/profile", label: "Profile", icon: <User className="h-4 w-4" /> },
  {
    to: "/settings/integrations",
    label: "Integrations",
    icon: <Sparkles className="h-4 w-4" />,
  },
  { to: "/settings/team", label: "Team", icon: <Users className="h-4 w-4" /> },
  {
    to: "/settings/danger",
    label: "Danger zone",
    icon: <AlertTriangle className="h-4 w-4" />,
    danger: true,
  },
];

/**
 * SettingsLayout — world-class settings shell
 *
 * Layout: 2-column on lg+ (left rail + content), stacked on mobile.
 * - Left rail: user mini-card + section nav (sticky, scrollable)
 * - Mobile: horizontal scroll pills at top + content below
 *
 * URL-based sub-routes (shareable, browser-back/forward, deep-linkable):
 *   /settings            → redirect to /settings/profile
 *   /settings/profile
 *   /settings/integrations
 *   /settings/team
 *   /settings/danger
 */
export function SettingsLayout() {
  const user = useAuthStore((s) => s.user);
  const me = useMe(true);

  const displayEmail = me.data?.email ?? user?.email ?? "";
  const displayName =
    me.data?.full_name ?? displayEmail.split("@")[0] ?? "User";
  const displayRole = me.data?.role ?? user?.role ?? "user";
  const displayInitial = (displayEmail[0] ?? "U").toUpperCase();

  return (
    <div className="animate-fade-in">
      {/* Mobile section nav (horizontal scroll pills) */}
      <div className="lg:hidden mb-6 -mx-4 px-4 overflow-x-auto">
        <nav className="flex gap-2 pb-2">
          {SECTIONS.map((section) => (
            <NavLink
              key={section.to}
              to={section.to}
              end
              className={({ isActive }) =>
                cn(
                  "flex items-center gap-2 px-3 py-1.5 rounded-full text-sm font-medium whitespace-nowrap transition-all duration-150 ease-out-expo border flex-shrink-0",
                  isActive
                    ? section.danger
                      ? "bg-rose-100 text-rose-700 border-rose-200"
                      : "bg-foreground text-background border-foreground"
                    : "bg-background text-muted-foreground border-border hover:text-foreground",
                )
              }
            >
              {section.icon}
              {section.label}
            </NavLink>
          ))}
        </nav>
      </div>

      {/* Desktop: 2-column with sticky left rail */}
      <div className="grid grid-cols-1 lg:grid-cols-[16rem_1fr] gap-8">
        {/* Left rail (desktop only) */}
        <aside className="hidden lg:block lg:sticky lg:top-20 lg:self-start space-y-4">
          {/* User mini-card */}
          <div className="rounded-lg border border-border bg-card p-4">
            <div className="flex items-center gap-3">
              <div className="h-11 w-11 rounded-full bg-gradient-to-br from-violet-500 to-indigo-600 flex items-center justify-center text-white font-semibold shadow-glow-sm flex-shrink-0">
                {displayInitial}
              </div>
              <div className="min-w-0 flex-1">
                <p className="text-sm font-medium truncate">{displayName}</p>
                <p className="text-xs text-muted-foreground truncate">
                  {displayEmail}
                </p>
              </div>
            </div>
            <div className="mt-3 flex items-center gap-1.5 text-xs text-muted-foreground">
              <ShieldCheck className="h-3 w-3" />
              <span className="capitalize">{displayRole}</span>
            </div>
          </div>

          {/* Section nav */}
          <nav className="space-y-1">
            {SECTIONS.map((section) => (
              <NavLink
                key={section.to}
                to={section.to}
                end
                className={({ isActive }) =>
                  cn(
                    "flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-all duration-150 ease-out-expo",
                    isActive
                      ? section.danger
                        ? "bg-rose-50 text-rose-700 border border-rose-200"
                        : "bg-accent text-accent-foreground"
                      : "text-muted-foreground hover:text-foreground hover:bg-muted",
                  )
                }
              >
                {section.icon}
                {section.label}
              </NavLink>
            ))}
          </nav>
        </aside>

        {/* Content (Outlet for active section) */}
        <main className="min-w-0">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
