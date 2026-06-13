import { NavLink } from "react-router-dom";
import {
  LayoutDashboard,
  Users,
  KanbanSquare,
  Sparkles,
} from "lucide-react";
import { cn } from "@/lib/utils";

const navItems = [
  { to: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { to: "/prospects", label: "Prospects", icon: Users },
  { to: "/pipeline", label: "Pipeline", icon: KanbanSquare },
  // Settings moved to Topbar avatar dropdown (PR #23 audit fix)
  // — single source of truth, less sidebar clutter
];

/**
 * Sidebar — per UI/UX Playbook §7.6
 *
 * Fixes (T9 audit):
 * - Removed user footer (avatar + email + role). Moved user
 *   identity to Topbar avatar dropdown (single source of truth).
 * - h-screen (was min-h-screen) ensures aside is exactly
 *   viewport height, so sticky top-0 actually sticks.
 * - flex-1 + overflow-y-auto on nav lets the nav itself scroll
 *   if many items are added in future (T6 sequences, etc.).
 */
export function Sidebar() {
  return (
    <aside className="hidden md:flex w-60 bg-sidebar-gradient text-slate-100 h-screen sticky top-0 flex-col border-r border-slate-800/50">
      {/* Brand block */}
      <div className="p-5 border-b border-slate-800/50 flex-shrink-0">
        <NavLink
          to="/dashboard"
          className="flex items-center gap-2.5 group"
        >
          <div className="h-9 w-9 rounded-lg bg-gradient-to-br from-violet-500 to-indigo-600 flex items-center justify-center shadow-glow-sm transition-transform duration-200 group-hover:scale-105">
            <Sparkles className="h-5 w-5 text-white" />
          </div>
          <div>
            <h1 className="text-base font-bold leading-none text-white">
              ClientFinder
            </h1>
            <p className="text-[10px] text-slate-400 mt-0.5 uppercase tracking-wider font-medium">
              AI Agent
            </p>
          </div>
        </NavLink>
      </div>

      {/* Nav (scrollable if many items) */}
      <nav className="flex-1 p-3 space-y-1 overflow-y-auto">
        {navItems.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end
            className={({ isActive }) =>
              cn(
                "flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all duration-150 ease-out-expo",
                isActive
                  ? "bg-gradient-to-r from-violet-600/20 to-indigo-600/10 text-white border border-violet-500/30 shadow-glow-sm"
                  : "text-slate-400 hover:text-white hover:bg-slate-800/50",
              )
            }
          >
            {({ isActive }) => (
              <>
                <item.icon
                  className={cn(
                    "h-4 w-4 transition-colors",
                    isActive ? "text-violet-300" : "",
                  )}
                />
                {item.label}
              </>
            )}
          </NavLink>
        ))}
      </nav>
    </aside>
  );
}
