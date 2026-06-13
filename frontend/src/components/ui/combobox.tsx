import { useEffect, useRef, useState } from "react";
import { Check, ChevronsUpDown, Search } from "lucide-react";
import { cn } from "@/lib/utils";

export interface ComboboxOption {
  value: string;
  label: string;
  sublabel?: string;
  icon?: React.ReactNode;
  pill?: React.ReactNode;
}

export interface ComboboxProps {
  options: ComboboxOption[];
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  emptyMessage?: string;
  disabled?: boolean;
  className?: string;
  onSearchChange?: (query: string) => void;
  /** Visual size variant */
  size?: "sm" | "md";
}

/**
 * Combobox — searchable select.
 *
 * World-class replacement for native `<select>`. Features:
 * - Search-as-you-type filter (label + sublabel)
 * - Optional async search via onSearchChange
 * - Each option supports label + sublabel + icon + pill (e.g. grade)
 * - Keyboard nav (Tab + Enter) + click-outside to close
 * - Selected value shown with pill + icon in trigger
 * - Renders into a Popover-style overlay (z-50)
 *
 * Reused by: Outreach composer (prospect + hook + template pickers).
 */
export function Combobox({
  options,
  value,
  onChange,
  placeholder = "Select…",
  emptyMessage = "Tidak ada hasil",
  disabled = false,
  className,
  onSearchChange,
  size = "md",
}: ComboboxProps) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [open]);

  const selected = options.find((o) => o.value === value);
  const q = query.trim().toLowerCase();
  const filtered = q
    ? options.filter(
        (o) =>
          o.label.toLowerCase().includes(q) ||
          (o.sublabel?.toLowerCase().includes(q) ?? false),
      )
    : options;

  return (
    <div ref={ref} className={cn("relative", className)}>
      <button
        type="button"
        disabled={disabled}
        onClick={() => setOpen(!open)}
        className={cn(
          "w-full rounded-md border border-input bg-background text-sm flex items-center justify-between gap-2 transition-colors",
          "hover:bg-muted/30 focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-1",
          disabled && "opacity-50 cursor-not-allowed",
          !selected && "text-muted-foreground",
          size === "sm" ? "h-8 px-2.5" : "min-h-9 h-auto py-1.5 px-3",
        )}
      >
        <span className="flex items-center gap-2 flex-1 min-w-0 text-left">
          {selected?.icon}
          {selected ? (
            <span className="flex items-center gap-2 min-w-0 truncate">
              <span className="truncate">{selected.label}</span>
              {selected.pill}
              {selected.sublabel && (
                <span className="text-xs text-muted-foreground truncate">
                  {selected.sublabel}
                </span>
              )}
            </span>
          ) : (
            <span>{placeholder}</span>
          )}
        </span>
        <ChevronsUpDown className="h-4 w-4 flex-shrink-0 text-muted-foreground" />
      </button>
      {open && (
        <div
          className={cn(
            "absolute z-50 mt-1 w-full min-w-[240px] rounded-md border border-border bg-popover shadow-lg flex flex-col animate-fade-in",
          )}
        >
          <div className="p-2 border-b border-border">
            <div className="relative">
              <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground pointer-events-none" />
              <input
                autoFocus
                value={query}
                onChange={(e) => {
                  setQuery(e.target.value);
                  onSearchChange?.(e.target.value);
                }}
                placeholder="Cari…"
                className="w-full h-8 pl-8 pr-2 text-sm rounded border border-input bg-background"
              />
            </div>
          </div>
          <ul className="overflow-y-auto max-h-60 p-1">
            {filtered.length === 0 ? (
              <li className="px-3 py-3 text-sm text-muted-foreground text-center">
                {emptyMessage}
              </li>
            ) : (
              filtered.map((o) => (
                <li key={o.value}>
                  <button
                    type="button"
                    onClick={() => {
                      onChange(o.value);
                      setOpen(false);
                      setQuery("");
                    }}
                    className={cn(
                      "w-full px-2 py-1.5 text-sm rounded flex items-center gap-2 hover:bg-accent transition-colors text-left",
                      o.value === value && "bg-accent",
                    )}
                  >
                    {o.icon}
                    <span className="flex-1 min-w-0 truncate">
                      {o.label}
                    </span>
                    {o.sublabel && (
                      <span className="text-xs text-muted-foreground truncate">
                        {o.sublabel}
                      </span>
                    )}
                    {o.pill}
                    {o.value === value && (
                      <Check className="h-3.5 w-3.5 flex-shrink-0 text-violet-600" />
                    )}
                  </button>
                </li>
              ))
            )}
          </ul>
        </div>
      )}
    </div>
  );
}
