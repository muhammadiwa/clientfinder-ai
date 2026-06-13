import { Link } from "react-router-dom";
import type { ReactNode } from "react";

import { cn } from "@/lib/utils";

interface LayoutProps {
  children: ReactNode;
}

/**
 * Top-level authenticated layout:
 * - Sidebar (left) with nav links
 * - Topbar with user menu
 * - Main content area
 */
export function Layout({ children }: LayoutProps) {
  return (
    <div className="min-h-screen bg-background text-foreground">
      <div className="flex">
        <Sidebar />
        <div className="flex-1 flex flex-col">
          <Topbar />
          <main className={cn("flex-1 p-6")}>{children}</main>
        </div>
      </div>
    </div>
  );
}

function Sidebar() {
  const navItems = [
    { to: "/dashboard", label: "Dashboard" },
    { to: "/prospects", label: "Prospects" },
    { to: "/pipeline", label: "Pipeline" },
    { to: "/settings", label: "Settings" },
  ];

  return (
    <aside className="w-56 border-r bg-card min-h-screen sticky top-0">
      <div className="p-6 border-b">
        <h1 className="text-lg font-bold">ClientFinder</h1>
        <p className="text-xs text-muted-foreground">AI Agent v0.1.0</p>
      </div>
      <nav className="p-3 space-y-1">
        {navItems.map((item) => (
          <Link
            key={item.to}
            to={item.to}
            className="block px-3 py-2 rounded-md text-sm hover:bg-accent hover:text-accent-foreground transition-colors"
          >
            {item.label}
          </Link>
        ))}
      </nav>
    </aside>
  );
}

function Topbar() {
  return (
    <header className="h-14 border-b bg-card flex items-center justify-between px-6">
      <div className="text-sm text-muted-foreground">T3 Group 3: Router + Layout</div>
      <div className="text-sm text-muted-foreground">admin@clientfinder.app</div>
    </header>
  );
}
