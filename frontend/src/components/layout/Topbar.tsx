import { useEffect } from "react";
import { Link, useNavigate } from "react-router-dom";
import { LogOut, User as UserIcon } from "lucide-react";
import { toast } from "react-hot-toast";

import { Button } from "@/components/ui/button";
import { useAuthStore } from "@/stores/auth";
import { useMe, useLogout } from "@/hooks/useAuth";
import { MobileNav } from "./MobileNav";

export function Topbar() {
  const navigate = useNavigate();
  const { isAuthenticated, user } = useAuthStore();
  const me = useMe(isAuthenticated);
  const logout = useLogout();

  useEffect(() => {
    if (isAuthenticated && me.isError) {
      useAuthStore.getState().clearAuth();
      navigate("/login");
    }
  }, [isAuthenticated, me.isError, navigate]);

  const handleLogout = async () => {
    try {
      await logout.mutateAsync();
      toast.success("Signed out");
      navigate("/login");
    } catch {
      toast.error("Logout failed (but signed out locally)");
      useAuthStore.getState().clearAuth();
      navigate("/login");
    }
  };

  return (
    <header className="h-14 border-b bg-card flex items-center justify-between px-4 md:px-6">
      <div className="flex items-center gap-2">
        <MobileNav />
        <h2 className="text-sm font-semibold md:hidden">ClientFinder</h2>
      </div>
      <div className="flex items-center gap-3">
        <div className="hidden sm:flex items-center gap-2 text-sm text-muted-foreground">
          <UserIcon className="h-4 w-4" />
          <span>{me.data?.email ?? user?.email ?? "guest"}</span>
        </div>
        {isAuthenticated ? (
          <Button
            variant="ghost"
            size="sm"
            onClick={handleLogout}
            disabled={logout.isPending}
          >
            <LogOut className="h-4 w-4" />
            <span className="hidden sm:inline">Sign out</span>
          </Button>
        ) : (
          <Button asChild variant="ghost" size="sm">
            <Link to="/login">Sign in</Link>
          </Button>
        )}
      </div>
    </header>
  );
}
