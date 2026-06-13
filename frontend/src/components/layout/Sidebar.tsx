import { NavLink } from "react-router-dom";
import { LayoutDashboard, Users, KanbanSquare, Settings } from "lucide-react";
import { cn } from "@/lib/utils";

const navItems = [
  { to: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { to: "/prospects", label: "Prospects", icon: Users },
  { to: "/pipeline", label: "Pipeline", icon: KanbanSquare },
  { to: "/settings", label: "Settings", icon: Settings },
];

export function Sidebar() {
  return (
    <aside className="hidden md:flex w-56 border-r bg-card min-h-screen sticky top-0 flex-col">
      <div className="p-6 border-b">
        <h1 className="text-lg font-bold">ClientFinder</h1>
        <p className="text-xs text-muted-foreground">AI Agent v0.1.0</p>
      </div>
      <nav className="flex-1 p-3 space-y-1">
        {navItems.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end
            className={({ isActive }) =>
              cn(
                "flex items-center gap-3 px-3 py-2 rounded-md text-sm transition-colors",
                isActive
                  ? "bg-primary text-primary-foreground font-medium"
                  : "hover:bg-accent hover:text-accent-foreground",
              )
            }
          >
            <item.icon className="h-4 w-4" />
            {item.label}
          </NavLink>
        ))}
      </nav>
      <div className="p-3 border-t text-xs text-muted-foreground">
        <p className="px-3">T3 Group 6 of 7</p>
        <p className="px-3">Sidebar w/ icons + active</p>
      </div>
    </aside>
  );
}
