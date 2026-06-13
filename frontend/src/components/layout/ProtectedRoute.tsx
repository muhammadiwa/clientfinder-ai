import { Navigate, useLocation } from "react-router-dom";
import type { ReactNode } from "react";

import { useAuthStore } from "@/stores/auth";

interface ProtectedRouteProps {
  children: ReactNode;
}

/**
 * Wrap any route that requires authentication.
 * Redirects to /login if no valid token, preserving the
 * intended destination for post-login redirect.
 */
export function ProtectedRoute({ children }: ProtectedRouteProps) {
  const { accessToken } = useAuthStore();
  const location = useLocation();

  if (!accessToken) {
    return <Navigate to="/login" state={{ from: location.pathname }} replace />;
  }

  return <>{children}</>;
}
