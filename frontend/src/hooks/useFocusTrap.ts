import { useEffect, useRef } from "react";

/**
 * useFocusTrap — traps keyboard focus within a container.
 *
 * Used by modals/dialogs. Pressing Tab on the last focusable
 * element cycles to the first; Shift+Tab on the first cycles
 * to the last. Restores focus to the previously focused element
 * on cleanup.
 *
 * A11y reference: WAI-ARIA Authoring Practices — Modal Dialog.
 */
export function useFocusTrap<T extends HTMLElement>(
  active: boolean = true,
) {
  const containerRef = useRef<T | null>(null);
  const previouslyFocusedRef = useRef<HTMLElement | null>(null);

  useEffect(() => {
    if (!active) return;
    const container = containerRef.current;
    if (!container) return;

    // Remember what was focused so we can restore on close
    previouslyFocusedRef.current = document.activeElement as HTMLElement;

    // Find all focusable elements
    const getFocusable = (): HTMLElement[] => {
      const sel = [
        "a[href]",
        "button:not([disabled])",
        "input:not([disabled])",
        "textarea:not([disabled])",
        "select:not([disabled])",
        "[tabindex]:not([tabindex='-1'])",
      ].join(",");
      return Array.from(
        container.querySelectorAll<HTMLElement>(sel),
      ).filter(
        (el) => !el.hasAttribute("aria-hidden") && el.tabIndex !== -1,
      );
    };

    // Focus the first focusable element after mount
    const focusables = getFocusable();
    if (focusables.length > 0) {
      // Slight delay so the dialog can mount first
      setTimeout(() => focusables[0]?.focus(), 0);
    } else {
      // If nothing focusable, focus the container itself
      container.focus();
    }

    // Trap Tab + Shift+Tab
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key !== "Tab") return;
      const currentFocusables = getFocusable();
      if (currentFocusables.length === 0) {
        e.preventDefault();
        return;
      }
      const first = currentFocusables[0];
      const last = currentFocusables[currentFocusables.length - 1];
      const activeEl = document.activeElement as HTMLElement;

      if (e.shiftKey) {
        if (activeEl === first || !container.contains(activeEl)) {
          e.preventDefault();
          last.focus();
        }
      } else {
        if (activeEl === last || !container.contains(activeEl)) {
          e.preventDefault();
          first.focus();
        }
      }
    };

    document.addEventListener("keydown", handleKeyDown);

    return () => {
      document.removeEventListener("keydown", handleKeyDown);
      // Restore focus on close
      const prev = previouslyFocusedRef.current;
      if (prev && typeof prev.focus === "function") {
        prev.focus();
      }
    };
  }, [active]);

  return containerRef;
}
