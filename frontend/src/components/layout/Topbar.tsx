import { useEffect } from "react";
import { Link, useNavigate, useLocation } from "react-router-dom";
import {
  Search,
  Bell,
  ChevronRight,
  Sparkles,
  LogOut,
  User as UserIcon,
  Settings,
  ShieldCheck,
} from "lucide-react";
import { toast } from "react-hot-toast";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { useAuthStore } from "@/stores/auth";
import { useMe, useLogout } from "@/hooks/useAuth";
import { MobileNav } from "./MobileNav";
import {
  DropdownMenu,
  MenuHeader,
  MenuItem,
  MenuSeparator,
} from "@/components/ui/dropdown-menu";
import { cn } from "@/lib/utils";

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

  const pathSegments = location.pathname.split("/").filter(Boolean);
  const breadcrumb = pathSegments.map((seg, idx) => ({
    label: routeLabels[seg] ?? seg,
    path: "/" + pathSegments.slice(0, idx + 1).join("/"),
    isLast: idx === pathSegments.length - 1,
  }));

  const displayEmail = me.data?.email ?? user?.email ?? "";
  const displayRole = me.data?.role ?? user?.role ?? "user";
  const displayInitial = (displayEmail[0] ?? "U").toUpperCase();
  const displayName = me.data?.full_name ?? displayEmail.split("@")[0] ?? "User";

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
        <Link to="/dashboard" className="flex md:hidden items-center gap-2">
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
        {/* Search (lg+ only) */}
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

        {/* User menu (avatar + dropdown) */}
        {isAuthenticated ? (
          <DropdownMenu
            align="right"
            width="w-60"
            trigger={
              <button
                type="button"
                aria-label="User menu"
                className={cn(
                  "h-9 w-9 rounded-full flex items-center justify-center text-white font-semibold text-sm",
                  "bg-gradient-to-br from-violet-500 to-indigo-600",
                  "shadow-glow-sm",
                  "transition-all duration-150 ease-out-expo",
                  "hover:scale-105 hover:shadow-glow active:scale-95",
                  "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2",
                )}
              >
                {displayInitial}
              </button>
            }
          >
            <MenuHeader>
              <p className="text-sm font-medium text-foreground truncate">
                {displayName}
              </p>
              <p className="text-xs text-muted-foreground truncate">
                {displayEmail}
              </p>
              <p className="text-[10px] text-muted-foreground capitalize mt-0.5 flex items-center gap-1">
                <ShieldCheck className="h-2.5 w-2.5" />
                {displayRole}
              </p>
            </MenuHeader>

            <MenuItem
              to="/settings"
              icon={<Settings className="h-4 w-4" />}
            >
              Settings
            </MenuItem>

            <MenuSeparator />

            <MenuItem
              onClick={handleLogout}
              variant="destructive"
              icon={<LogOut className="h-4 w-4" />}
              disabled={logout.isPending}
            >
              {logout.isPending ? "Signing out…" : "Sign out"}
            </MenuItem>
          </DropdownMenu>
        ) : (
          <Button asChild variant="ghost" size="sm">
            <Link to="/login">Sign in</Link>
          </Button>
        )}
      </div>
    </header>
  );
}
