import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import {
  Inbox,
  Send,
  CheckCircle2,
  XCircle,
  Loader2,
  Sparkles,
  Mail,
  MessageSquare,
  AlertTriangle,
  ChevronRight,
  Copy,
  Check,
  Clock,
  RotateCcw,
  Trash2,
  ChevronDown,
  Plus,
} from "lucide-react";
import { toast } from "react-hot-toast";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/ui/empty-state";
import {
  approveMessage,
  createMessage,
  deleteMessage,
  generateMessage,
  listMessages,
  sendMessage,
  submitForApproval,
  type MessageGenerateRequest,
} from "@/api/outreach";
import { useProspects } from "@/hooks/useProspects";
import { getProspectDetail } from "@/api/prospects";
import type { Message, MessageChannel } from "@/types";
import { cn } from "@/lib/utils";

type Tab = "pending_approval" | "drafts" | "sent" | "failed";

const TABS: { id: Tab; label: string; icon: React.ReactNode }[] = [
  { id: "pending_approval", label: "Pending approval", icon: <Inbox className="h-4 w-4" /> },
  { id: "drafts", label: "Drafts", icon: <Clock className="h-4 w-4" /> },
  { id: "sent", label: "Sent", icon: <Send className="h-4 w-4" /> },
  { id: "failed", label: "Failed", icon: <XCircle className="h-4 w-4" /> },
];

/**
 * Outreach page — the R10 human-in-the-loop review queue + composer.
 *
 * Tabs (filter by status):
 *   - Pending approval (the R10 review queue — needs human sign-off)
 *   - Drafts (still being edited)
 *   - Sent (delivery confirmation)
 *   - Failed (resend or fix)
 *
 * Composer (left rail): pick prospect + hook + channel → generate →
 * edit → submit for approval → approve → send.
 */
export function OutreachPage() {
  const [tab, setTab] = useState<Tab>("pending_approval");
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(true);
  const [reloadKey, setReloadKey] = useState(0);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);

  // Composer state
  const [composerProspectId, setComposerProspectId] = useState<string>("");
  const [composerHookId, setComposerHookId] = useState<string>("");
  const [composerChannel, setComposerChannel] = useState<MessageChannel>("email");
  const [composerGenerated, setComposerGenerated] = useState<{
    subject: string;
    body: string;
  } | null>(null);
  const [composerLoading, setComposerLoading] = useState(false);
  const [composerCopied, setComposerCopied] = useState(false);

  // Fetch messages
  const fetchMessages = async () => {
    setLoading(true);
    try {
      const filters: { page: number; per_page: number; status?: string } = {
        page: 1,
        per_page: 50,
      };
      if (tab === "pending_approval") {
        // /messages?status=pending_approval
        filters.status = "pending_approval";
      } else if (tab === "drafts") {
        filters.status = "draft";
      } else if (tab === "sent") {
        filters.status = "sent";
      } else if (tab === "failed") {
        filters.status = "failed";
      }
      const data = await listMessages(filters);
      setMessages(data.items);
    } catch {
      toast.error("Failed to load messages");
    } finally {
      setLoading(false);
    }
  };

  // Refetch when tab or reloadKey changes
  useMemo(() => {
    fetchMessages();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tab, reloadKey]);

  // Composer: list of prospects (recent)
  const { data: prospectsData } = useProspects({ per_page: 30 });
  const composerProspects = prospectsData?.items ?? [];
  const selectedProspect = composerProspects.find(
    (p) => p.id === composerProspectId,
  );

  // Load hooks for selected prospect
  const [prospectHooks, setProspectHooks] = useState<
    { id: string; hook_text: string; recommended_service: string | null }[]
  >([]);
  useMemo(() => {
    if (!composerProspectId) {
      setProspectHooks([]);
      setComposerHookId("");
      return;
    }
    getProspectDetail(composerProspectId)
      .then((d) => {
        setProspectHooks(
          d.hooks.map((h) => ({
            id: h.id,
            hook_text: h.hook_text,
            recommended_service: h.recommended_service,
          })),
        );
        setComposerHookId(d.hooks[0]?.id ?? "");
      })
      .catch(() => setProspectHooks([]));
  }, [composerProspectId]);

  // Actions
  const reload = () => setReloadKey((k) => k + 1);

  const handleApprove = async (m: Message) => {
    setBusyId(m.id);
    try {
      await approveMessage(m.id, { approve: true });
      toast.success("Approved");
      reload();
    } catch {
      toast.error("Approval failed");
    } finally {
      setBusyId(null);
    }
  };

  const handleReject = async (m: Message) => {
    const reason = prompt("Reason for rejection (optional):") || undefined;
    setBusyId(m.id);
    try {
      await approveMessage(m.id, { approve: false, reason });
      toast.success("Rejected");
      reload();
    } catch {
      toast.error("Reject failed");
    } finally {
      setBusyId(null);
    }
  };

  const handleSend = async (m: Message) => {
    setBusyId(m.id);
    try {
      await sendMessage(m.id);
      toast.success("Sent (check Sent tab for status)");
      reload();
    } catch {
      toast.error("Send failed");
    } finally {
      setBusyId(null);
    }
  };

  const handleSubmit = async (m: Message) => {
    setBusyId(m.id);
    try {
      await submitForApproval(m.id);
      toast.success("Submitted for approval");
      reload();
    } catch {
      toast.error("Submit failed");
    } finally {
      setBusyId(null);
    }
  };

  const handleDelete = async (m: Message) => {
    if (!confirm("Delete this message? Cannot be undone.")) return;
    setBusyId(m.id);
    try {
      await deleteMessage(m.id);
      toast.success("Deleted");
      reload();
    } catch {
      toast.error("Delete failed (sent messages cannot be deleted)");
    } finally {
      setBusyId(null);
    }
  };

  // Composer actions
  const handleGenerate = async () => {
    if (!composerProspectId || !composerHookId) {
      toast.error("Pick a prospect + hook first");
      return;
    }
    setComposerLoading(true);
    try {
      const payload: MessageGenerateRequest = {
        prospect_id: composerProspectId,
        hook_id: composerHookId,
        channel: composerChannel,
      };
      // false = preview only (don't create draft yet)
      const m = await generateMessage(payload, false);
      setComposerGenerated({ subject: m.subject ?? "", body: m.body });
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Generate failed");
    } finally {
      setComposerLoading(false);
    }
  };

  const handleCreateDraft = async () => {
    if (!composerGenerated || !composerProspectId || !composerHookId) {
      toast.error("Generate first");
      return;
    }
    setComposerLoading(true);
    try {
      await createMessage({
        prospect_id: composerProspectId,
        channel: composerChannel,
        subject: composerGenerated.subject || "(no subject)",
        body: composerGenerated.body,
        hook_id: composerHookId,
      });
      toast.success(`Draft created — switch to Drafts tab to submit`);
      setComposerGenerated(null);
      reload();
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Create failed");
    } finally {
      setComposerLoading(false);
    }
  };

  const handleCopyBody = async (text: string) => {
    try {
      await navigator.clipboard.writeText(text);
      setComposerCopied(true);
      toast.success("Copied to clipboard");
      setTimeout(() => setComposerCopied(false), 2000);
    } catch {
      toast.error("Copy failed");
    }
  };

  // Tab counts
  const counts: Record<Tab, number> = {
    pending_approval: messages.length,
    drafts: 0,
    sent: 0,
    failed: 0,
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-[1fr_400px] gap-6 animate-fade-in">
      {/* Main column: tabs + message list */}
      <div className="space-y-4 min-w-0">
        {/* Header */}
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Outreach</h1>
          <p className="text-muted-foreground mt-1 text-sm">
            R10 review queue — approve messages before they send
          </p>
        </div>

        {/* Tabs */}
        <div className="flex items-center gap-1 border-b border-border overflow-x-auto">
          {TABS.map((t) => (
            <button
              key={t.id}
              type="button"
              onClick={() => setTab(t.id)}
              className={cn(
                "flex items-center gap-2 px-4 py-2.5 text-sm font-medium border-b-2 transition-colors whitespace-nowrap",
                tab === t.id
                  ? "border-violet-500 text-foreground"
                  : "border-transparent text-muted-foreground hover:text-foreground",
              )}
            >
              {t.icon}
              {t.label}
              {t.id === "pending_approval" && counts.pending_approval > 0 && (
                <span className="ml-1 inline-flex items-center justify-center min-w-5 h-5 px-1.5 rounded-full bg-violet-600 text-white text-xs font-bold">
                  {counts.pending_approval}
                </span>
              )}
            </button>
          ))}
        </div>

        {/* Message list */}
        {loading ? (
          <div className="space-y-2">
            {Array.from({ length: 4 }).map((_, i) => (
              <Skeleton key={i} className="h-20" />
            ))}
          </div>
        ) : messages.length === 0 ? (
          <EmptyState
            className="py-12"
            icon={
              tab === "pending_approval" ? (
                <CheckCircle2 className="h-5 w-5 text-emerald-500" />
              ) : tab === "drafts" ? (
                <Sparkles className="h-5 w-5" />
              ) : tab === "sent" ? (
                <Send className="h-5 w-5" />
              ) : (
                <MessageSquare className="h-5 w-5" />
              )
            }
            title={
              tab === "pending_approval"
                ? "All caught up"
                : tab === "drafts"
                  ? "No drafts"
                  : tab === "sent"
                    ? "Nothing sent yet"
                    : "No failures"
            }
            description={
              tab === "pending_approval"
                ? "No messages waiting for review"
                : tab === "drafts"
                  ? "Use the composer to create a draft"
                  : tab === "sent"
                    ? "Approved messages you send will show here"
                    : "Failed sends will appear here with error details"
            }
          />
        ) : (
          <ul className="space-y-2">
            {messages.map((message) => (
              <MessageRow
                key={message.id}
                m={message}
                expanded={expandedId === message.id}
                onToggle={() =>
                  setExpandedId(
                    expandedId === message.id ? null : message.id,
                  )
                }
                busy={busyId === message.id}
                onApprove={() => handleApprove(message)}
                onReject={() => handleReject(message)}
                onSend={() => handleSend(message)}
                onSubmit={() => handleSubmit(message)}
                onDelete={() => handleDelete(message)}
              />
            ))}
          </ul>
        )}
      </div>

      {/* Right rail: composer */}
      <aside className="space-y-4 lg:sticky lg:top-20 lg:self-start lg:max-h-[calc(100vh-6rem)] lg:overflow-y-auto pr-1">
        <Card>
          <CardHeader>
            <CardTitle className="text-base flex items-center gap-2">
              <Sparkles className="h-4 w-4" />
              Compose new
            </CardTitle>
            <CardDescription>
              Pick a prospect + hook → AI expands to email/WhatsApp
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {/* Prospect picker */}
            <div>
              <label className="text-xs font-medium text-muted-foreground">
                Prospect
              </label>
              <select
                value={composerProspectId}
                onChange={(e) => setComposerProspectId(e.target.value)}
                className="mt-1 w-full h-9 rounded-md border border-input bg-background px-2 text-sm"
              >
                <option value="">— Pick a prospect —</option>
                {composerProspects.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.company_name} · {p.quality_grade ?? "?"}
                  </option>
                ))}
              </select>
            </div>

            {/* Hook picker */}
            {composerProspectId && (
              <div>
                <label className="text-xs font-medium text-muted-foreground">
                  Hook
                </label>
                <select
                  value={composerHookId}
                  onChange={(e) => setComposerHookId(e.target.value)}
                  className="mt-1 w-full h-9 rounded-md border border-input bg-background px-2 text-sm"
                >
                  <option value="">— Pick a hook —</option>
                  {prospectHooks.map((h) => (
                    <option key={h.id} value={h.id}>
                      {h.hook_text.slice(0, 60)}…
                    </option>
                  ))}
                </select>
                {prospectHooks.length === 0 && (
                  <p className="text-xs text-amber-600 mt-1">
                    No hooks yet — generate them on the prospect detail
                    page first.
                  </p>
                )}
              </div>
            )}

            {/* Channel */}
            <div>
              <label className="text-xs font-medium text-muted-foreground">
                Channel
              </label>
              <div className="grid grid-cols-2 gap-1.5 mt-1">
                {(["email", "whatsapp"] as MessageChannel[]).map((c) => (
                  <button
                    key={c}
                    type="button"
                    onClick={() => setComposerChannel(c)}
                    className={cn(
                      "h-9 rounded-md text-sm font-medium border transition-colors flex items-center justify-center gap-1.5",
                      composerChannel === c
                        ? "bg-violet-600 text-white border-violet-600"
                        : "bg-background border-border text-muted-foreground hover:text-foreground",
                    )}
                  >
                    {c === "email" ? (
                      <Mail className="h-3.5 w-3.5" />
                    ) : (
                      <MessageSquare className="h-3.5 w-3.5" />
                    )}
                    {c}
                  </button>
                ))}
              </div>
            </div>

            <Button
              onClick={handleGenerate}
              disabled={composerLoading || !composerHookId}
              className="w-full"
              size="sm"
            >
              {composerLoading ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Sparkles className="h-4 w-4" />
              )}
              Generate
            </Button>

            {/* Generated preview */}
            {composerGenerated && (
              <div className="mt-2 p-3 rounded-lg border border-violet-200 bg-violet-50/50 dark:bg-violet-950/20 space-y-2">
                {composerGenerated.subject && (
                  <div>
                    <p className="text-[10px] uppercase tracking-wider text-violet-700 font-semibold">
                      Subject
                    </p>
                    <p className="text-sm font-medium mt-0.5">
                      {composerGenerated.subject}
                    </p>
                  </div>
                )}
                <div>
                  <p className="text-[10px] uppercase tracking-wider text-violet-700 font-semibold">
                    Body
                  </p>
                  <p className="text-sm leading-relaxed mt-0.5 whitespace-pre-wrap max-h-60 overflow-y-auto">
                    {composerGenerated.body}
                  </p>
                </div>
                <div className="flex items-center gap-2 pt-1">
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => handleCopyBody(composerGenerated.body)}
                  >
                    {composerCopied ? (
                      <Check className="h-3.5 w-3.5" />
                    ) : (
                      <Copy className="h-3.5 w-3.5" />
                    )}
                    Copy
                  </Button>
                  <Button
                    size="sm"
                    onClick={handleCreateDraft}
                    disabled={composerLoading}
                  >
                    <Plus className="h-3.5 w-3.5" />
                    Save as draft
                  </Button>
                </div>
              </div>
            )}
          </CardContent>
        </Card>

        {selectedProspect && (
          <Card>
            <CardContent className="p-4">
              <Link
                to={`/prospects/${selectedProspect.id}`}
                className="flex items-center justify-between gap-2 text-sm hover:text-violet-600"
              >
                <div className="min-w-0">
                  <p className="font-medium truncate">
                    {selectedProspect.company_name}
                  </p>
                  <p className="text-xs text-muted-foreground">
                    View full analysis
                  </p>
                </div>
                <ChevronRight className="h-4 w-4 flex-shrink-0" />
              </Link>
            </CardContent>
          </Card>
        )}
      </aside>
    </div>
  );
}

// --- Sub-components ---

interface MessageRowProps {
  m: Message;
  expanded: boolean;
  busy: boolean;
  onToggle: () => void;
  onApprove: () => void;
  onReject: () => void;
  onSend: () => void;
  onSubmit: () => void;
  onDelete: () => void;
}

function MessageRow({
  m,
  expanded,
  busy,
  onToggle,
  onApprove,
  onReject,
  onSend,
  onSubmit,
  onDelete,
}: MessageRowProps) {
  const channelIcon =
    m.channel === "email" ? (
      <Mail className="h-3.5 w-3.5" />
    ) : m.channel === "whatsapp" ? (
      <MessageSquare className="h-3.5 w-3.5" />
    ) : (
      <MessageSquare className="h-3.5 w-3.5" />
    );

  return (
    <li className="rounded-lg border border-border bg-card overflow-hidden">
      {/* Header row */}
      <button
        type="button"
        onClick={onToggle}
        className="w-full p-3 text-left flex items-start gap-3 hover:bg-muted/30 transition-colors"
        disabled={busy}
      >
        <div className="flex-shrink-0 mt-0.5 text-muted-foreground">
          {channelIcon}
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span
              className={cn(
                "inline-flex items-center gap-1 text-[10px] font-bold uppercase tracking-wider px-1.5 py-0.5 rounded",
                STATUS_BADGE[m.status]?.className ?? "bg-muted",
              )}
            >
              {m.status.replace("_", " ")}
            </span>
            <span className="text-xs text-muted-foreground capitalize">
              {m.channel}
            </span>
            {m.error_message && (
              <span className="inline-flex items-center gap-1 text-xs text-rose-600">
                <AlertTriangle className="h-3 w-3" />
                error
              </span>
            )}
          </div>
          <p className="text-sm font-medium mt-1 truncate">
            {m.subject || m.body.slice(0, 80) || "(no subject)"}
          </p>
          <p className="text-xs text-muted-foreground mt-0.5 line-clamp-1">
            {m.body.slice(0, 120)}
          </p>
        </div>
        <div className="flex-shrink-0 text-muted-foreground">
          {busy ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <ChevronDown
              className={cn(
                "h-4 w-4 transition-transform",
                expanded && "rotate-180",
              )}
            />
          )}
        </div>
      </button>

      {/* Expanded details */}
      {expanded && (
        <div className="border-t border-border p-3 bg-muted/20 space-y-3">
          {m.subject && (
            <div>
              <p className="text-[10px] uppercase tracking-wider text-muted-foreground font-semibold mb-0.5">
                Subject
              </p>
              <p className="text-sm font-medium">{m.subject}</p>
            </div>
          )}
          <div>
            <p className="text-[10px] uppercase tracking-wider text-muted-foreground font-semibold mb-0.5">
              Body
            </p>
            <p className="text-sm leading-relaxed whitespace-pre-wrap max-h-80 overflow-y-auto">
              {m.body}
            </p>
          </div>
          {m.error_message && (
            <div className="p-2 rounded-md bg-rose-50 dark:bg-rose-950/30 border border-rose-200">
              <p className="text-xs text-rose-700 font-mono">
                {m.error_message}
              </p>
            </div>
          )}
          {/* Actions by status */}
          <div className="flex flex-wrap items-center gap-2 pt-1">
            {m.status === "pending_approval" && (
              <>
                <Button size="sm" onClick={onApprove} disabled={busy}>
                  <CheckCircle2 className="h-3.5 w-3.5" />
                  Approve
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={onReject}
                  disabled={busy}
                >
                  <XCircle className="h-3.5 w-3.5" />
                  Reject
                </Button>
              </>
            )}
            {m.status === "approved" && (
              <Button size="sm" onClick={onSend} disabled={busy}>
                <Send className="h-3.5 w-3.5" />
                Send now
              </Button>
            )}
            {m.status === "failed" && (
              <>
                <Button size="sm" onClick={onSend} disabled={busy}>
                  <RotateCcw className="h-3.5 w-3.5" />
                  Retry send
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={onSubmit}
                  disabled={busy}
                >
                  Re-approve
                </Button>
              </>
            )}
            {m.status === "draft" && (
              <Button size="sm" onClick={onSubmit} disabled={busy}>
                <Inbox className="h-3.5 w-3.5" />
                Submit for approval
              </Button>
            )}
            {(m.status === "draft" ||
              m.status === "pending_approval" ||
              m.status === "rejected" ||
              m.status === "failed") && (
              <Button
                size="sm"
                variant="ghost"
                onClick={onDelete}
                disabled={busy}
                className="text-rose-600 hover:text-rose-700"
              >
                <Trash2 className="h-3.5 w-3.5" />
                Delete
              </Button>
            )}
            {m.status === "sent" && (
              <span className="text-xs text-muted-foreground">
                Sent at {m.sent_at ? formatTime(m.sent_at) : "—"}
              </span>
            )}
          </div>
        </div>
      )}
    </li>
  );
}

const STATUS_BADGE: Record<string, { className: string }> = {
  draft: { className: "bg-slate-100 text-slate-700" },
  pending_approval: {
    className: "bg-amber-100 text-amber-700",
  },
  approved: { className: "bg-sky-100 text-sky-700" },
  scheduled: { className: "bg-violet-100 text-violet-700" },
  sending: { className: "bg-blue-100 text-blue-700" },
  sent: { className: "bg-emerald-100 text-emerald-700" },
  delivered: { className: "bg-emerald-100 text-emerald-700" },
  opened: { className: "bg-emerald-100 text-emerald-700" },
  clicked: { className: "bg-emerald-100 text-emerald-700" },
  replied: { className: "bg-emerald-100 text-emerald-700" },
  bounced: { className: "bg-rose-100 text-rose-700" },
  failed: { className: "bg-rose-100 text-rose-700" },
  rejected: { className: "bg-zinc-100 text-zinc-700" },
};

function formatTime(iso: string): string {
  try {
    return new Date(iso).toLocaleString("id-ID", {
      day: "numeric",
      month: "short",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return iso;
  }
}
