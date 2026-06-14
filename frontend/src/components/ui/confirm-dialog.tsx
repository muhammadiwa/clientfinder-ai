import { useEffect } from "react";
import { createPortal } from "react-dom";
import { Loader2, X } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Label, Textarea } from "@/components/ui/input";
import { useFocusTrap } from "@/hooks/useFocusTrap";
import { cn } from "@/lib/utils";
import { useT, getT } from "@/i18n";

export interface ConfirmDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  description?: React.ReactNode;
  /** Optional inline input (for Reject reason, etc.) */
  input?: {
    label: string;
    placeholder?: string;
    value: string;
    onChange: (v: string) => void;
  };
  confirmText?: string;
  cancelText?: string;
  destructive?: boolean;
  loading?: boolean;
  onConfirm: () => void | Promise<void>;
}

/**
 * ConfirmDialog — in-app modal dialog (world-class replacement
 * for native `confirm()` and `prompt()`).
 *
 * Per T4 audit (A3) + T6 audit (F1): used everywhere we previously
 * called `window.confirm()` or `window.prompt()`.
 *
 * - Portal-rendered (z-50, escapes stacking contexts)
 * - Backdrop click + Esc to close (when not loading)
 * - Optional inline input (for Reject reason)
 * - Destructive variant for delete actions
 * - Loading state for async operations
 */
export function ConfirmDialog({
  open,
  onOpenChange,
  title,
  description,
  input,
  confirmText = getT().confirmDialog.defaultConfirmText,
  cancelText = getT().confirmDialog.defaultCancelText,
  destructive = false,
  loading = false,
  onConfirm,
}: ConfirmDialogProps) {
  const t = useT();
  // Focus trap — cycles Tab within dialog, restores focus on close
  const dialogRef = useFocusTrap<HTMLDivElement>(open);
  // Esc to close
  useEffect(() => {
    if (!open) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape" && !loading) {
        onOpenChange(false);
      }
    };
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, [open, loading, onOpenChange]);

  if (!open) return null;
  if (typeof document === "undefined") return null;

  return createPortal(
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 animate-fade-in">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/60 backdrop-blur-sm"
        onClick={() => !loading && onOpenChange(false)}
        aria-hidden
      />
      {/* Dialog */}
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal
        aria-labelledby="confirm-dialog-title"
        className={cn(
          "relative bg-card border border-border rounded-xl shadow-2xl max-w-md w-full p-6 space-y-4",
          "animate-fade-in focus:outline-none",
        )}
      >
        <div className="flex items-start justify-between gap-3">
          <h2
            id="confirm-dialog-title"
            className="text-lg font-semibold leading-tight"
          >
            {title}
          </h2>
          <button
            type="button"
            onClick={() => onOpenChange(false)}
            disabled={loading}
            className="text-muted-foreground hover:text-foreground p-1 -mt-1 -mr-1"
            aria-label={t.confirmDialog.ariaClose}
          >
            <X className="h-4 w-4" />
          </button>
        </div>
        {description && (
          <p className="text-sm text-muted-foreground leading-relaxed">
            {description}
          </p>
        )}
        {input && (
          <div className="space-y-1.5">
            <Label htmlFor="confirm-input">{input.label}</Label>
            <Textarea
              id="confirm-input"
              value={input.value}
              onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) =>
                input.onChange(e.target.value)
              }
              placeholder={input.placeholder}
              rows={3}
              autoFocus
              className="resize-none"
            />
          </div>
        )}
        <div className="flex justify-end gap-2 pt-1">
          <Button
            variant="outline"
            onClick={() => onOpenChange(false)}
            disabled={loading}
          >
            {cancelText}
          </Button>
          <Button
            variant={destructive ? "destructive" : "default"}
            onClick={() => onConfirm()}
            disabled={loading}
          >
            {loading && <Loader2 className="h-4 w-4 animate-spin" />}
            {confirmText}
          </Button>
        </div>
      </div>
    </div>,
    document.body,
  );
}
