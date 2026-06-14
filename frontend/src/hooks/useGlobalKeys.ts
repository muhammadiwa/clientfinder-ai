import { useEffect } from "react";
import { useLocation } from "react-router-dom";

/**
 * useGlobalKeys — global keyboard shortcuts.
 *
 * T8.5+ Group 3: power-user shortcuts.
 * - g d / g s / g p / g o / g a: go to Dashboard / Scout / Prospects / Outreach / Analytics
 * - ?: show keyboard shortcuts help (T8.5+)
 * - /: focus the search input on the current page (if any)
 *
 * Avoids firing while the user is typing in an input/textarea.
 */
export function useGlobalKeys(handlers: {
  onShowHelp?: () => void;
  onSearch?: () => void;
  onGoTo?: (path: string) => void;
}) {
  const location = useLocation();

  useEffect(() => {
    let gPressedAt: number | null = null;
    const onKey = (e: KeyboardEvent) => {
      // Don't intercept while typing
      const target = e.target as HTMLElement | null;
      if (
        target &&
        (target.tagName === "INPUT" ||
          target.tagName === "TEXTAREA" ||
          target.isContentEditable)
      ) {
        return;
      }
      // Ignore when modifier keys are held
      if (e.metaKey || e.ctrlKey || e.altKey) return;

      // g-prefix shortcuts: g + letter within 1.2s
      if (e.key === "g" && !gPressedAt) {
        gPressedAt = Date.now();
        return;
      }
      if (gPressedAt && Date.now() - gPressedAt < 1200) {
        const map: Record<string, string> = {
          d: "/dashboard",
          s: "/scout",
          p: "/prospects",
          o: "/outreach",
          a: "/analytics",
        };
        if (map[e.key] && handlers.onGoTo) {
          e.preventDefault();
          handlers.onGoTo(map[e.key]);
        }
        gPressedAt = null;
        return;
      }
      gPressedAt = null;

      // ? — show shortcuts help
      if (e.key === "?" && handlers.onShowHelp) {
        e.preventDefault();
        handlers.onShowHelp();
        return;
      }
      // / — focus search
      if (e.key === "/" && handlers.onSearch) {
        e.preventDefault();
        handlers.onSearch();
        return;
      }
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [handlers, location.pathname]);
}
