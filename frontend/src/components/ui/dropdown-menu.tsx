import { useEffect, useRef, useState } from "react";
import { cn } from "@/lib/utils";
import type { ReactNode } from "react";

interface DropdownMenuProps {
  /** Trigger element (button, avatar, etc.) */
  trigger: ReactNode;
  /** Dropdown content (MenuItem, MenuLabel, MenuSeparator, etc.) */
  children: ReactNode;
  /** Alignment relative to trigger */
  align?: "left" | "right";
  /** Width of dropdown content */
  width?: string;
  /** Additional class for the wrapper */
  className?: string;
}

/**
 * DropdownMenu — world-class dropdown primitive per audit findings
 *
 * Features:
 * - Click trigger to toggle
 * - Click outside to close
 * - Escape key to close
 * - Smooth fade + scale-in animation
 * - Keyboard accessible (focus stays on trigger when closed)
 * - Portal-free (simple, predictable positioning)
 */
export function DropdownMenu({
  trigger,
  children,
  align = "right",
  width = "w-56",
  className,
}: DropdownMenuProps) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const handleClick = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false);
    };
    document.addEventListener("mousedown", handleClick);
    document.addEventListener("keydown", handleEscape);
    return () => {
      document.removeEventListener("mousedown", handleClick);
      document.removeEventListener("keydown", handleEscape);
    };
  }, [open]);

  return (
    <div className={cn("relative", className)} ref={ref}>
      <div
        onClick={() => setOpen((o) => !o)}
        className="cursor-pointer"
      >
        {trigger}
      </div>
      {open && (
        <div
          role="menu"
          className={cn(
            "absolute top-full mt-2 z-50 rounded-lg border border-border bg-card shadow-lg overflow-hidden",
            "animate-fade-in",
            align === "right" ? "right-0" : "left-0",
            width,
          )}
        >
          {children}
        </div>
      )}
    </div>
  );
}

interface MenuItemProps {
  children: ReactNode;
  onClick?: () => void;
  href?: string;
  to?: string;
  variant?: "default" | "destructive";
  icon?: ReactNode;
  disabled?: boolean;
}

import { Link } from "react-router-dom";

export function MenuItem({
  children,
  onClick,
  href,
  to,
  variant = "default",
  icon,
  disabled,
}: MenuItemProps) {
  const baseClasses = cn(
    "flex items-center gap-2.5 w-full px-3 py-2 text-sm transition-colors duration-150",
    "focus:outline-none",
    variant === "destructive"
      ? "text-rose-600 hover:bg-rose-50 dark:hover:bg-rose-950/30"
      : "text-foreground hover:bg-muted",
    disabled && "opacity-50 pointer-events-none",
  );

  const content = (
    <>
      {icon && <span className="text-muted-foreground">{icon}</span>}
      <span className="flex-1 text-left">{children}</span>
    </>
  );

  if (to) {
    return (
      <Link
        to={to}
        role="menuitem"
        className={baseClasses}
        onClick={onClick}
      >
        {content}
      </Link>
    );
  }

  if (href) {
    return (
      <a
        href={href}
        role="menuitem"
        className={baseClasses}
        onClick={onClick}
      >
        {content}
      </a>
    );
  }

  return (
    <button
      type="button"
      role="menuitem"
      className={baseClasses}
      onClick={onClick}
      disabled={disabled}
    >
      {content}
    </button>
  );
}

export function MenuLabel({ children }: { children: ReactNode }) {
  return (
    <div className="px-3 py-2 text-xs text-muted-foreground uppercase tracking-wider font-medium">
      {children}
    </div>
  );
}

export function MenuSeparator() {
  return <div className="h-px bg-border my-1" />;
}

export function MenuHeader({ children }: { children: ReactNode }) {
  return <div className="px-3 py-2.5 bg-muted/40 border-b">{children}</div>;
}
