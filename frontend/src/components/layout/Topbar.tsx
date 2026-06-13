import { Link } from "react-router-dom";
import { LogOut } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { toast } from "react-hot-toast";

import { Button } from "@/components/ui/button";
import { useAuthStore } from "@/stores/auth";
import { useMe, useLogout } from "@/hooks/useAuth";
import { useEffect } from "react";

export function Topbar() {
  const navigate = useNavigate();
  const { isAuthenticated, user } = useAuthStore();
  const me = useMe(isAuthenticated);
  const logout = useLogout();

  // On mount, if we have a token, refresh user data
  useEffect(() => {
    if (isAuthenticated && me.isError) {
      // Token likely invalid, clear
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
    <header className="h-14 border-b bg-card flex items-center justify-between px-6">
      <div className="text-sm text-muted-foreground">ClientFinder AI Agent</div>
      <div className="flex items-center gap-4">
        <span className="text-sm text-muted-foreground">
          {me.data?.email ?? user?.email ?? "guest"}
        </span>
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
