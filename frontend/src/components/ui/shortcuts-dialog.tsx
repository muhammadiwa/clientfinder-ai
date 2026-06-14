import { createPortal } from "react-dom";
import { X } from "lucide-react";
import { useEffect } from "react";

import { Button } from "@/components/ui/button";
import { useFocusTrap } from "@/hooks/useFocusTrap";

export interface KeyboardShortcutsDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

/**
 * KeyboardShortcutsDialog — help dialog showing all available
 * keyboard shortcuts in the app.
 *
 * A11y: focus trapped, Esc to close, role=dialog + aria-modal.
 */
export function KeyboardShortcutsDialog({
  open,
  onOpenChange,
}: KeyboardShortcutsDialogProps) {
  const ref = useFocusTrap<HTMLDivElement>(open);

  useEffect(() => {
    if (!open) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") onOpenChange(false);
    };
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, [open, onOpenChange]);

  if (!open || typeof document === "undefined") return null;

  const shortcuts = [
    {
      category: "Navigasi",
      items: [
        { keys: ["g", "d"], description: "Buka Dashboard" },
        { keys: ["g", "s"], description: "Buka Scout" },
        { keys: ["g", "p"], description: "Buka Prospek" },
        { keys: ["g", "o"], description: "Buka Outreach" },
        { keys: ["g", "a"], description: "Buka Analitik" },
      ],
    },
    {
      category: "Aksi",
      items: [
        { keys: ["?"], description: "Tampilkan pintasan keyboard" },
        { keys: ["/"], description: "Fokus ke pencarian" },
        { keys: ["Esc"], description: "Tutup dialog" },
      ],
    },
    {
      category: "Outreach (saat fokus di pesan)",
      items: [
        { keys: ["A"], description: "Setujui pesan" },
        { keys: ["R"], description: "Tolak pesan" },
        { keys: ["S"], description: "Kirim pesan" },
        { keys: ["J"], description: "Pesan berikutnya" },
        { keys: ["K"], description: "Pesan sebelumnya" },
      ],
    },
  ];

  return createPortal(
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 animate-fade-in">
      <div
        className="absolute inset-0 bg-black/60 backdrop-blur-sm"
        onClick={() => onOpenChange(false)}
        aria-hidden
      />
      <div
        ref={ref}
        role="dialog"
        aria-modal
        aria-labelledby="shortcuts-title"
        className="relative bg-card border border-border rounded-xl shadow-2xl max-w-lg w-full p-6 space-y-4 animate-fade-in focus:outline-none"
      >
        <div className="flex items-start justify-between gap-3">
          <h2
            id="shortcuts-title"
            className="text-lg font-semibold leading-tight"
          >
            Pintasan keyboard
          </h2>
          <button
            type="button"
            onClick={() => onOpenChange(false)}
            className="text-muted-foreground hover:text-foreground p-1 -mt-1 -mr-1"
            aria-label="Tutup"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        <div className="space-y-5">
          {shortcuts.map((section) => (
            <div key={section.category}>
              <h3 className="text-xs uppercase tracking-wider text-muted-foreground font-semibold mb-2">
                {section.category}
              </h3>
              <ul className="space-y-1.5">
                {section.items.map((item, i) => (
                  <li
                    key={i}
                    className="flex items-center justify-between text-sm"
                  >
                    <span className="text-muted-foreground">
                      {item.description}
                    </span>
                    <span className="flex items-center gap-1">
                      {item.keys.map((k, j) => (
                        <kbd
                          key={j}
                          className="px-1.5 py-0.5 text-xs font-mono bg-muted border border-border rounded"
                        >
                          {k}
                        </kbd>
                      ))}
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        <div className="flex justify-end pt-2 border-t border-border">
          <Button
            variant="outline"
            size="sm"
            onClick={() => onOpenChange(false)}
          >
            Tutup
          </Button>
        </div>
      </div>
    </div>,
    document.body,
  );
}
