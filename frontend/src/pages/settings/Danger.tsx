import {
  AlertTriangle,
  Trash2,
  Download,
  KeyRound,
} from "lucide-react";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

/**
 * Settings / Danger zone section
 * Muted styling (border, text) — actions are disabled until T8.
 * Per audit finding #4: visually communicates "not actionable yet".
 */
export function DangerSection() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-rose-700/80">
          Danger zone
        </h1>
        <p className="text-muted-foreground mt-1 text-sm">
          Irreversible actions. Proceed with caution.
        </p>
      </div>

      <Card className="border-rose-200/50">
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2 text-rose-700/80">
            <AlertTriangle className="h-4 w-4" />
            Destructive actions
          </CardTitle>
          <CardDescription>
            These actions permanently affect your workspace. Confirmation
            dialogs come in T8.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          {/* Export data */}
          <DangerRow
            icon={<Download className="h-4 w-4" />}
            title="Export all data"
            description="Download a complete backup of your prospects, messages, and settings as JSON."
            actionLabel="Export"
            disabled
            disabledReason="Available in T8"
          />

          {/* Rotate API key */}
          <DangerRow
            icon={<KeyRound className="h-4 w-4" />}
            title="Rotate API key"
            description="Generate a new secret for any active integration. Old key will stop working immediately."
            actionLabel="Rotate"
            disabled
            disabledReason="Available in T8"
          />

          {/* Delete account */}
          <DangerRow
            icon={<Trash2 className="h-4 w-4" />}
            title="Delete account"
            description="Permanently delete your account and all associated data. This cannot be undone."
            actionLabel="Delete account"
            danger
            disabled
            disabledReason="Available in T8"
          />
        </CardContent>
      </Card>
    </div>
  );
}

interface DangerRowProps {
  icon: React.ReactNode;
  title: string;
  description: string;
  actionLabel: string;
  danger?: boolean;
  disabled?: boolean;
  disabledReason?: string;
}

function DangerRow({
  icon,
  title,
  description,
  actionLabel,
  danger = false,
  disabled = false,
  disabledReason,
}: DangerRowProps) {
  return (
    <div
      className={`flex items-center justify-between gap-4 p-4 rounded-lg border ${
        danger
          ? "border-rose-200/50 bg-rose-50/30"
          : "border-border bg-muted/20"
      }`}
    >
      <div className="flex items-start gap-3 min-w-0">
        <div
          className={`h-9 w-9 rounded-lg flex items-center justify-center flex-shrink-0 ${
            danger
              ? "bg-rose-100 text-rose-700"
              : "bg-muted text-muted-foreground"
          }`}
        >
          {icon}
        </div>
        <div className="min-w-0 flex-1">
          <p className="text-sm font-medium">{title}</p>
          <p className="text-xs text-muted-foreground mt-0.5">{description}</p>
        </div>
      </div>
      <Button
        variant="outline"
        size="sm"
        disabled={disabled}
        title={disabledReason}
        className={danger ? "border-rose-200" : ""}
      >
        {actionLabel}
      </Button>
    </div>
  );
}
