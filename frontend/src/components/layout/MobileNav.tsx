import { useState } from "react";
import { NavLink } from "react-router-dom";
import {
  LayoutDashboard,
  Users,
  KanbanSquare,
  Settings,
  Menu,
  X,
} from "lucide-react";
import { cn } from "@/lib/utils";

const navItems = [
  { to: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { to: "/prospects", label: "Prospects", icon: Users },
  { to: "/pipeline", label: "Pipeline", icon: KanbanSquare },
  { to: "/settings", label: "Settings", icon: Settings },
];

/**
 * MobileNav — drawer for mobile (md:hidden)
 * - Hamburger button in Topbar
 * - Slide-out from left with backdrop
 * - Same nav items + active state as Sidebar (dark)
 */
export function MobileNav() {
  const [open, setOpen] = useState(false);

  return (
    <>
      <button
        type="button"
        className="md:hidden p-2 -ml-2 rounded-md hover:bg-accent text-foreground"
        onClick={() => setOpen(true)}
        aria-label="Open menu"
      >
        <Menu className="h-5 w-5" />
      </button>

      {open && (
        <>
          <div
            className="fixed inset-0 z-40 bg-slate-900/50 backdrop-blur-sm md:hidden animate-fade-in"
            onClick={() => setOpen(false)}
          />
          <aside className="fixed inset-y-0 left-0 z-50 w-72 bg-sidebar-gradient text-slate-100 md:hidden flex flex-col border-r border-slate-800/50 animate-slide-in-right">
            <div className="flex items-center justify-between p-5 border-b border-slate-800/50">
              <h1 className="text-base font-bold text-white">ClientFinder</h1>
              <button
                type="button"
                onClick={() => setOpen(false)}
                className="p-1 rounded-md text-slate-400 hover:text-white hover:bg-slate-800/50"
                aria-label="Close menu"
              >
                <X className="h-5 w-5" />
              </button>
            </div>
            <nav className="flex-1 p-3 space-y-1">
              {navItems.map((item) => (
                <NavLink
                  key={item.to}
                  to={item.to}
                  end
                  onClick={() => setOpen(false)}
                  className={({ isActive }) =>
                    cn(
                      "flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all duration-150",
                      isActive
                        ? "bg-gradient-to-r from-violet-600/20 to-indigo-600/10 text-white border border-violet-500/30"
                        : "text-slate-400 hover:text-white hover:bg-slate-800/50",
                    )
                  }
                >
                  <item.icon className="h-4 w-4" />
                  {item.label}
                </NavLink>
              ))}
            </nav>
          </aside>
        </>
      )}
    </>
  );
}
