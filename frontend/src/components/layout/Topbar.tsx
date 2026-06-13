import { useEffect } from "react";
import { Link, useNavigate, useLocation } from "react-router-dom";
import {
  LogOut,
  Search,
  Bell,
  ChevronRight,
  Sparkles,
} from "lucide-react";
import { toast } from "react-hot-toast";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { useAuthStore } from "@/stores/auth";
import { useMe, useLogout } from "@/hooks/useAuth";
import { MobileNav } from "./MobileNav";
import { cn } from "@/lib/utils";

/**
 * Topbar — per UI/UX Playbook §7.6
 * - Glass effect (backdrop-blur + bg-card/80)
 * - Subtle border-b
 * - Mobile: hamburger + brand
 * - Desktop: breadcrumb (left) + search + notifications + user menu (right)
 */

const routeLabels: Record<string, string> = {
  dashboard: "Dashboard",
  prospects: "Prospects",
  pipeline: "Pipeline",
  settings: "Settings",
};

export function Topbar() {
  const navigate = useNavigate();
  const location = useLocation();
  const { isAuthenticated, user, clearAuth } = useAuthStore();
  const me = useMe(isAuthenticated);
  const logout = useLogout();
  const [search, setSearch] = useState("");

  useEffect(() => {
    if (isAuthenticated && me.isError) {
      clearAuth();
      navigate("/login");
    }
  }, [isAuthenticated, me.isError, navigate, clearAuth]);

  const handleLogout = async () => {
    try {
      await logout.mutateAsync();
      toast.success("Signed out");
      navigate("/login");
    } catch {
      toast.error("Signed out locally");
      clearAuth();
      navigate("/login");
    }
  };

  // Build breadcrumb from current path
  const pathSegments = location.pathname.split("/").filter(Boolean);
  const breadcrumb = pathSegments.map((seg, idx) => ({
    label: routeLabels[seg] ?? seg,
    path: "/" + pathSegments.slice(0, idx + 1).join("/"),
    isLast: idx === pathSegments.length - 1,
  }));

  return (
    <header
      className={cn(
        "h-14 border-b border-border/60 flex items-center justify-between px-4 md:px-6 sticky top-0 z-30",
        "glass",
      )}
    >
      <div className="flex items-center gap-2 md:gap-4 flex-1 min-w-0">
        <MobileNav />

        {/* Mobile brand */}
        <Link
          to="/dashboard"
          className="flex md:hidden items-center gap-2"
        >
          <div className="h-7 w-7 rounded-md bg-gradient-to-br from-violet-500 to-indigo-600 flex items-center justify-center text-white">
            <Sparkles className="h-4 w-4" />
          </div>
          <span className="text-sm font-semibold">ClientFinder</span>
        </Link>

        {/* Desktop breadcrumb */}
        <nav className="hidden md:flex items-center gap-1 text-sm">
          {breadcrumb.length === 0 ? (
            <span className="text-muted-foreground">ClientFinder</span>
          ) : (
            <>
              <Link
                to="/dashboard"
                className="text-muted-foreground hover:text-foreground transition-colors"
              >
                ClientFinder
              </Link>
              {breadcrumb.map((crumb) => (
                <span key={crumb.path} className="flex items-center gap-1">
                  <ChevronRight className="h-3.5 w-3.5 text-muted-foreground/50" />
                  {crumb.isLast ? (
                    <span className="text-foreground font-medium">
                      {crumb.label}
                    </span>
                  ) : (
                    <Link
                      to={crumb.path}
                      className="text-muted-foreground hover:text-foreground transition-colors"
                    >
                      {crumb.label}
                    </Link>
                  )}
                </span>
              ))}
            </>
          )}
        </nav>
      </div>

      <div className="flex items-center gap-2 md:gap-3">
        {/* Search (desktop only) */}
        <div className="hidden lg:flex relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <input
            type="search"
            placeholder="Search…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="h-9 w-64 pl-9 pr-3 rounded-md border border-input bg-background/50 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-1 placeholder:text-muted-foreground transition-colors"
          />
        </div>

        {/* Notifications (placeholder) */}
        <Button
          variant="ghost"
          size="icon"
          className="relative"
          aria-label="Notifications"
        >
          <Bell className="h-4 w-4" />
          <span className="absolute top-2 right-2 h-2 w-2 rounded-full bg-rose-500" />
        </Button>

        {/* User email + sign out */}
        {isAuthenticated ? (
          <div className="hidden sm:flex items-center gap-2">
            <span className="text-sm text-muted-foreground hidden md:inline">
              {me.data?.email ?? user?.email}
            </span>
            <Button
              variant="ghost"
              size="icon"
              onClick={handleLogout}
              disabled={logout.isPending}
              aria-label="Sign out"
            >
              <LogOut className="h-4 w-4" />
            </Button>
          </div>
        ) : (
          <Button asChild variant="ghost" size="sm">
            <Link to="/login">Sign in</Link>
          </Button>
        )}
      </div>
    </header>
  );
}
