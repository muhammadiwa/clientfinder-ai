import { useState, type ReactNode } from "react";
import { useNavigate } from "react-router-dom";
import { cn } from "@/lib/utils";
import { KeyboardShortcutsDialog } from "@/components/ui/shortcuts-dialog";
import { useGlobalKeys } from "@/hooks/useGlobalKeys";
import { Sidebar } from "./Sidebar";
import { Topbar } from "./Topbar";

interface LayoutProps {
  children: ReactNode;
}

export function Layout({ children }: LayoutProps) {
  const navigate = useNavigate();
  const [helpOpen, setHelpOpen] = useState(false);

  // Global keyboard shortcuts: g+d/s/p/o/a (navigate), ? (help), / (search)
  useGlobalKeys({
    onShowHelp: () => setHelpOpen(true),
    onGoTo: (path) => navigate(path),
  });

  return (
    <div className="min-h-screen bg-background text-foreground">
      {/* Skip to main content link (a11y) */}
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:absolute focus:top-2 focus:left-2 focus:z-50 focus:px-4 focus:py-2 focus:bg-primary focus:text-primary-foreground focus:rounded-md focus:shadow-md"
      >
        Lewati ke konten utama
      </a>

      <div className="flex">
        <Sidebar />
        <div className="flex-1 flex flex-col min-w-0">
          <Topbar onShowHelp={() => setHelpOpen(true)} />
          <main
            id="main-content"
            className={cn("flex-1 p-4 md:p-6 lg:p-8 focus:outline-none")}
            tabIndex={-1}
          >
            {children}
          </main>
        </div>
      </div>

      <KeyboardShortcutsDialog
        open={helpOpen}
        onOpenChange={setHelpOpen}
      />
    </div>
  );
}
