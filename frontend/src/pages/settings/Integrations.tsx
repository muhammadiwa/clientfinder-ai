import { Link } from "react-router-dom";
import {
  MessageSquare,
  Brain,
  Server,
  Check,
  ArrowUpRight,
} from "lucide-react";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

interface Integration {
  id: string;
  name: string;
  description: string;
  icon: React.ReactNode;
  iconBg: string;
  iconColor: string;
  status: "connected" | "configured" | "coming" | "not_configured";
  statusLabel: string;
  statusColor: string;
  docsHref?: string;
}

const INTEGRATIONS: Integration[] = [
  {
    id: "whatsapp",
    name: "WhatsApp (openWA)",
    description:
      "Multi-number WhatsApp gateway for outreach. Already deployed and connected.",
    icon: <MessageSquare className="h-5 w-5" />,
    iconBg: "bg-emerald-100 dark:bg-emerald-900/30",
    iconColor: "text-emerald-700 dark:text-emerald-400",
    status: "connected",
    statusLabel: "Connected",
    statusColor:
      "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400",
  },
  {
    id: "llm",
    name: "LLM providers",
    description:
      "Groq (primary, free) + Gemini (fallback, free). Used for hooks, pain analysis, and outreach personalization.",
    icon: <Brain className="h-5 w-5" />,
    iconBg: "bg-violet-100 dark:bg-violet-900/30",
    iconColor: "text-violet-700 dark:text-violet-400",
    status: "configured",
    statusLabel: "Configured",
    statusColor:
      "bg-violet-100 text-violet-700 dark:bg-violet-900/30 dark:text-violet-400",
  },
  {
    id: "smtp",
    name: "Email (Postfix)",
    description:
      "SMTP server for sending outreach emails. Self-hosted, open source, free.",
    icon: <Server className="h-5 w-5" />,
    iconBg: "bg-amber-100 dark:bg-amber-900/30",
    iconColor: "text-amber-700 dark:text-amber-400",
    status: "coming",
    statusLabel: "Coming in T6",
    statusColor:
      "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400",
  },
];

/**
 * Settings / Integrations section
 * Grid of integration cards (md:grid-cols-2 lg:grid-cols-2).
 * Per playbook §8.4 — card grid, not vertical stack.
 */
export function IntegrationsSection() {
  return (
    <div className="space-y-6">
      <div className="flex items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Integrations</h1>
          <p className="text-muted-foreground mt-1 text-sm">
            External services connected to ClientFinder
          </p>
        </div>
        <Button variant="outline" size="sm" asChild>
          <Link to="/docs/integrations">
            <ArrowUpRight className="h-3.5 w-3.5" />
            Setup guide
          </Link>
        </Button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {INTEGRATIONS.map((integration) => (
          <IntegrationCard key={integration.id} integration={integration} />
        ))}
      </div>
    </div>
  );
}

function IntegrationCard({ integration }: { integration: Integration }) {
  return (
    <Card className="relative overflow-hidden">
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between gap-3">
          <div
            className={`h-10 w-10 rounded-lg flex items-center justify-center flex-shrink-0 ${integration.iconBg} ${integration.iconColor}`}
          >
            {integration.icon}
          </div>
          <span
            className={`inline-flex items-center gap-1 text-xs font-medium px-2 py-0.5 rounded-full whitespace-nowrap ${integration.statusColor}`}
          >
            {integration.status === "connected" && <Check className="h-3 w-3" />}
            {integration.statusLabel}
          </span>
        </div>
        <CardTitle className="text-base mt-3">{integration.name}</CardTitle>
      </CardHeader>
      <CardContent>
        <CardDescription className="leading-relaxed">
          {integration.description}
        </CardDescription>
        <div className="mt-4 flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            disabled={integration.status === "coming"}
            title={
              integration.status === "coming"
                ? integration.statusLabel
                : `Configure ${integration.name}`
            }
          >
            Configure
          </Button>
          {integration.docsHref && (
            <Button variant="ghost" size="sm" asChild>
              <a href={integration.docsHref} target="_blank" rel="noreferrer">
                Docs
                <ArrowUpRight className="h-3 w-3" />
              </a>
            </Button>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
