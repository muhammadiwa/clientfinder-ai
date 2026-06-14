import { useEffect, useState } from "react";
import {
  Link,
  useNavigate,
  useLocation,
  useSearchParams,
} from "react-router-dom";
import {
  Search,
  Bell,
  ChevronRight,
  Sparkles,
  LogOut,
  Settings,
  ShieldCheck,
} from "lucide-react";
import { toast } from "react-hot-toast";

import { Button } from "@/components/ui/button";
import { LanguagePicker } from "@/components/ui/language-picker";
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
import { useT, getT } from "@/i18n";

const routeLabels: Record<string, string> = {
  dashboard: getT().nav.dashboard,
  prospects: getT().nav.prospects,
  pipeline: getT().nav.pipeline,
  settings: getT().nav.settings,
};

interface TopbarProps {
  onShowHelp?: () => void;
}

export function Topbar({ onShowHelp: _onShowHelp }: TopbarProps = {}) {
  const t = useT();
  // onShowHelp is wired in Layout via global keyboard shortcuts (?).
  // Kept as a prop for future topbar-level "?" button.
  void _onShowHelp;
  const navigate = useNavigate();
  const location = useLocation();
  const [searchParams] = useSearchParams();
  const { isAuthenticated, user, clearAuth } = useAuthStore();
  const me = useMe(isAuthenticated);
  const logout = useLogout();
  const [search, setSearch] = useState(searchParams.get("search") ?? "");

  useEffect(() => {
    if (isAuthenticated && me.isError) {
      clearAuth();
      navigate("/login");
    }
  }, [isAuthenticated, me.isError, navigate, clearAuth]);

  const handleLogout = async () => {
    try {
      await logout.mutateAsync();
      toast.success(t.auth.signedOut);
      navigate("/login");
    } catch {
      toast.error(t.auth.signedOutLocally);
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
        {/* Search (lg+ only) — navigates to /prospects with search param */}
        <form
          onSubmit={(e) => {
            e.preventDefault();
            if (search.trim()) {
              navigate(`/prospects?search=${encodeURIComponent(search.trim())}`);
            } else {
              navigate("/prospects");
            }
          }}
          className="hidden lg:flex relative"
        >
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground pointer-events-none" />
          <input
            type="search"
            placeholder={t.topbar.searchProspects}
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            aria-label={t.topbar.searchAriaLabel}
            className="h-10 pl-9 w-64"
          />
        </form>

        {/* Notifications (placeholder) */}
        <Button
          variant="ghost"
          size="icon"
          className="relative"
          aria-label={t.topbar.notifications}
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
                aria-label={t.topbar.userMenu}
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

             {/* T8.5++++++: language toggle. Lets the user
                 verify the i18n system end-to-end. */}
             <div className="px-1.5 py-1.5">
               <LanguagePicker />
             </div>

             <MenuSeparator />

             <MenuItem
               to="/settings"
               icon={<Settings className="h-4 w-4" />}
             >
               {t.nav.settings}
             </MenuItem>

             <MenuSeparator />

             <MenuItem
               onClick={handleLogout}
               variant="destructive"
               icon={<LogOut className="h-4 w-4" />}
               disabled={logout.isPending}
             >
               {logout.isPending ? "Signing out…" : t.auth.signOut}
             </MenuItem>
          </DropdownMenu>
        ) : (
          <Button asChild variant="ghost" size="sm">
            <Link to="/login">{t.auth.signIn}</Link>
          </Button>
        )}
      </div>
    </header>
  );
}
