import type { ReactNode } from "react";

import { cn } from "@/lib/utils";
import { Sidebar } from "./Sidebar";
import { Topbar } from "./Topbar";

interface LayoutProps {
  children: ReactNode;
}

/**
 * Top-level authenticated layout:
 * - Sidebar (desktop only, hidden on mobile via Sidebar)
 * - MobileNav (hamburger menu, mobile only)
 * - Topbar with user menu + sign out
 * - Main content area
 */
export function Layout({ children }: LayoutProps) {
  return (
    <div className="min-h-screen bg-background text-foreground">
      <div className="flex">
        <Sidebar />
        <div className="flex-1 flex flex-col min-w-0">
          <Topbar />
          <main className={cn("flex-1 p-4 md:p-6")}>{children}</main>
        </div>
      </div>
    </div>
  );
}
