import { useEffect, useMemo, useState } from "react";
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
  Search,
  Filter,
} from "lucide-react";
import { toast } from "react-hot-toast";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { FormField, Input, Textarea } from "@/components/ui/input";
import { useApplyOptimistic } from "@/hooks/useOptimisticMessages";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/ui/empty-state";
import { Combobox, type ComboboxOption } from "@/components/ui/combobox";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import {
  approveMessage,
  createMessage,
  deleteMessage,
  generateMessage,
  getOutreachStats,
  listMessages,
  listTemplates,
  sendMessage,
  submitForApproval,
  type MessageGenerateRequest,
  type MessageListFilters,
} from "@/api/outreach";
import { useProspects } from "@/hooks/useProspects";
import { getProspectDetail } from "@/api/prospects";
import { t } from "@/i18n/id";
import { formatApiError } from "@/lib/formatError";
import { cn } from "@/lib/utils";
import type { Message, MessageChannel, OutreachStats, Prospect, Template } from "@/types";

type Tab = "pending_approval" | "drafts" | "sent" | "failed";
type FilterChannel = "all" | MessageChannel;
type FilterGrade = "all" | "A" | "B" | "C" | "D";

// --- Style maps ---

const TABS: { id: Tab; label: string; icon: React.ReactNode }[] = [
  { id: "pending_approval", label: "Pending approval", icon: <Inbox className="h-3.5 w-3.5" /> },
  { id: "drafts", label: "Drafts", icon: <Clock className="h-3.5 w-3.5" /> },
  { id: "sent", label: "Sent", icon: <Send className="h-3.5 w-3.5" /> },
  { id: "failed", label: "Failed", icon: <XCircle className="h-3.5 w-3.5" /> },
];

const STATUS_BADGE: Record<string, { bg: string; label?: string }> = {
  draft: { bg: "bg-slate-100 text-slate-700" },
  pending_approval: { bg: "bg-amber-100 text-amber-800 ring-1 ring-amber-300" },
  approved: { bg: "bg-sky-100 text-sky-800" },
  scheduled: { bg: "bg-violet-100 text-violet-800" },
  sending: { bg: "bg-blue-100 text-blue-800" },
  sent: { bg: "bg-emerald-100 text-emerald-800" },
  delivered: { bg: "bg-emerald-100 text-emerald-800" },
  opened: { bg: "bg-emerald-100 text-emerald-800" },
  clicked: { bg: "bg-emerald-100 text-emerald-800" },
  replied: { bg: "bg-emerald-100 text-emerald-800" },
  bounced: { bg: "bg-rose-100 text-rose-800" },
  failed: { bg: "bg-rose-100 text-rose-800" },
  rejected: { bg: "bg-zinc-100 text-zinc-800" },
};

const CHANNEL_STYLE: Record<string, { bg: string; text: string; icon: React.ReactNode }> = {
  email: {
    bg: "bg-violet-100 dark:bg-violet-900/30",
    text: "text-violet-700 dark:text-violet-400",
    icon: <Mail className="h-4 w-4" />,
  },
  whatsapp: {
    bg: "bg-emerald-100 dark:bg-emerald-900/30",
    text: "text-emerald-700 dark:text-emerald-400",
    icon: <MessageSquare className="h-4 w-4" />,
  },
  threads: {
    bg: "bg-sky-100 dark:bg-sky-900/30",
    text: "text-sky-700 dark:text-sky-400",
    icon: <MessageSquare className="h-4 w-4" />,
  },
};

const GRADE_STYLE: Record<string, string> = {
  A: "bg-emerald-100 text-emerald-800 ring-1 ring-emerald-300",
  B: "bg-sky-100 text-sky-800 ring-1 ring-sky-300",
  C: "bg-amber-100 text-amber-800 ring-1 ring-amber-300",
  D: "bg-rose-100 text-rose-800 ring-1 ring-rose-300",
};

const DELIVERY_FUNNEL = ["sent", "delivered", "opened", "clicked", "replied"];

// --- Helpers ---

function getInitials(name: string): string {
  return name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((w) => w[0]?.toUpperCase() ?? "")
    .join("") || "?";
}

function formatRelativeId(iso: string | null): string {
  if (!iso) return "—";
  const then = new Date(iso).getTime();
  if (Number.isNaN(then)) return "—";
  const diff = Date.now() - then;
  if (diff < 0) return "baru saja";
  const sec = Math.floor(diff / 1000);
  if (sec < 60) return `${sec} dtk lalu`;
  const min = Math.floor(sec / 60);
  if (min < 60) return `${min} mnt lalu`;
  const hr = Math.floor(min / 60);
  if (hr < 24) return `${hr} jam lalu`;
  const days = Math.floor(hr / 24);
  if (days < 30) return `${days} hari lalu`;
  const months = Math.floor(days / 30);
  return `${months} bln lalu`;
}

function formatTimeShort(iso: string | null): string {
  if (!iso) return "—";
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

// --- Main page ---

export function OutreachPage() {
  // Tab + list state
  const [tab, setTab] = useState<Tab>("pending_approval");
  const [messages, setMessages] = useState<Message[]>([]);
  // T8.5+++++++ Group 2: optimistic UI helper for bulk
  // actions. Removes the given ids from the local
  // messages state immediately, reverts on error.
  const applyOptimistic = useApplyOptimistic(messages, setMessages);
  const [stats, setStats] = useState<OutreachStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [reloadKey, setReloadKey] = useState(0);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [prospectsById, setProspectsById] = useState<Record<string, Prospect>>({});

  // Filters
  const [filterChannel, setFilterChannel] = useState<FilterChannel>("all");
  const [filterGrade, setFilterGrade] = useState<FilterGrade>("all");
  const [search, setSearch] = useState("");

  // Bulk selection
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [bulkBusy, setBulkBusy] = useState(false);

  // Confirm dialogs
  const [rejectDialog, setRejectDialog] = useState<{
    messageId: string;
    reason: string;
  } | null>(null);
  const [deleteDialog, setDeleteDialog] = useState<{
    messageId: string;
  } | null>(null);
  const [rejectLoading, setRejectLoading] = useState(false);
  const [deleteLoading, setDeleteLoading] = useState(false);

  // Keyboard nav (focused message for shortcut actions)
  const [focusedId, setFocusedId] = useState<string | null>(null);

  // Composer state
  const [composerProspectId, setComposerProspectId] = useState("");
  const [composerHookId, setComposerHookId] = useState("");
  const [composerChannel, setComposerChannel] = useState<MessageChannel>("email");
  const [composerTemplateId, setComposerTemplateId] = useState("");
  const [composerSubject, setComposerSubject] = useState("");
  const [composerBody, setComposerBody] = useState("");
  const [composerErrors, setComposerErrors] = useState<{
    subject?: string;
    body?: string;
  }>({});
  const [composerLoading, setComposerLoading] = useState(false);
  const [composerGenerated, setComposerGenerated] = useState(false);

  // Data: prospects + templates
  const { data: prospectsData } = useProspects({ per_page: 100 });
  const [templates, setTemplates] = useState<Template[]>([]);
  useEffect(() => {
    listTemplates()
      .then((d) => setTemplates(d.items))
      .catch(() => undefined);
  }, []);

  // Stats fetch
  useEffect(() => {
    let cancelled = false;
    getOutreachStats()
      .then((data) => {
        if (!cancelled) setStats(data);
      })
      .catch(() => {
        // ignore — stats are decorative, not critical
      });
    return () => {
      cancelled = true;
    };
  }, [reloadKey]);

  // Messages fetch (proper useEffect, not useMemo)
  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setMessages([]);
    setSelectedIds(new Set());

    const params: MessageListFilters = { page: 1, per_page: 50 };

    if (tab === "pending_approval") params.status = "pending_approval";
    else if (tab === "drafts") params.status = "draft";
    else if (tab === "failed") params.status = "failed";
    else if (tab === "sent") {
      // "sent" tab includes all post-send states
      params.status = "sent"; // approximate — backend doesn't support IN
    }
    if (filterChannel !== "all") params.channel = filterChannel as MessageChannel;
    if (filterGrade !== "all") params.prospect_grade = filterGrade;

    listMessages(params)
      .then(async (data) => {
        if (cancelled) return;
        setMessages(data.items);
        // Hydrate prospect info for each message (look up by id)
        const ids = [...new Set(data.items.map((m) => m.prospect_id))];
        const missing = ids.filter((id) => !prospectsById[id]);
        if (missing.length > 0) {
          // Load via useProspects cache (already loaded)
          // For v1 simplicity, just attach what we have
        }
      })
      .catch(() => {
        if (!cancelled) toast.error(t.outreach.failedToLoad);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tab, filterChannel, filterGrade, reloadKey]);

  // Hydrate prospectsById from useProspects cache + filtered search
  useEffect(() => {
    if (!prospectsData) return;
    const map: Record<string, Prospect> = { ...prospectsById };
    for (const p of prospectsData.items) {
      map[p.id] = p;
    }
    setProspectsById(map);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [prospectsData]);

  // Client-side filter (search)
  const visibleMessages = useMemo(() => {
    if (!search.trim()) return messages;
    const q = search.toLowerCase();
    return messages.filter((m) => {
      const prospect = prospectsById[m.prospect_id];
      return (
        m.subject?.toLowerCase().includes(q) ||
        m.body.toLowerCase().includes(q) ||
        prospect?.company_name.toLowerCase().includes(q)
      );
    });
  }, [messages, prospectsById, search]);

  // Auto-focus first message on tab change
  useEffect(() => {
    if (visibleMessages.length > 0) {
      setFocusedId(visibleMessages[0].id);
    } else {
      setFocusedId(null);
    }
    setExpandedId(null);
  }, [tab, filterChannel, filterGrade]);

  // Hooks for selected prospect (composer)
  const [prospectHooks, setProspectHooks] = useState<
    { id: string; hook_text: string; recommended_service: string | null; confidence: number }[]
  >([]);
  useEffect(() => {
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
            confidence: h.confidence,
          })),
        );
        setComposerHookId(d.hooks[0]?.id ?? "");
      })
      .catch(() => setProspectHooks([]));
  }, [composerProspectId]);

  // --- Actions ---

  const reload = () => setReloadKey((k) => k + 1);

  const handleApprove = async (id: string) => {
    setBusyId(id);
    // T8.5+++++++ (mirror): optimistic UI for single approve.
    // Removes the message from the pending tab INSTANTLY
    // (the user sees the green Approve button flip to
    // "approved" status the moment they click), reverts
    // on error.
    try {
      await applyOptimistic([id], async () => {
        await approveMessage(id, { approve: true });
      });
      toast.success(t.outreach.approvedToast);
    } catch {
      toast.error(t.outreach.approvalFailed);
    } finally {
      setBusyId(null);
    }
  };

  const handleRejectClick = (id: string) => {
    setRejectDialog({ messageId: id, reason: "" });
  };

  const handleRejectConfirm = async () => {
    if (!rejectDialog) return;
    setRejectLoading(true);
    // T8.5+++++++ (mirror): optimistic UI for single reject.
    // Removes the message from the pending tab INSTANTLY
    // (the user sees the row disappear the moment they
    // click 'Confirm' in the reject dialog with reason),
    // reverts on error.
    const id = rejectDialog.messageId;
    const reason = rejectDialog.reason || undefined;
    try {
      await applyOptimistic([id], async () => {
        await approveMessage(id, { approve: false, reason });
      });
      toast.success(t.outreach.rejectedToast);
      setRejectDialog(null);
    } catch {
      toast.error(t.outreach.rejectFailed);
    } finally {
      setRejectLoading(false);
    }
  };

  const handleSend = async (id: string) => {
    setBusyId(id);
    try {
      await sendMessage(id);
      toast.success(t.outreach.sentToast);
      reload();
    } catch {
      toast.error(t.outreach.sendFailed);
    } finally {
      setBusyId(null);
    }
  };

  const handleSubmit = async (id: string) => {
    setBusyId(id);
    try {
      await submitForApproval(id);
      toast.success(t.outreach.submitted);
      reload();
    } catch {
      toast.error(t.outreach.submitFailed);
    } finally {
      setBusyId(null);
    }
  };

  const handleDeleteClick = (id: string) => {
    setDeleteDialog({ messageId: id });
  };

  const handleDeleteConfirm = async () => {
    if (!deleteDialog) return;
    setDeleteLoading(true);
    // T8.5+++++++ (mirror): optimistic UI for single delete.
    // Removes the message from the current tab INSTANTLY
    // (so the dialog feels snappy), reverts on error.
    const id = deleteDialog.messageId;
    try {
      await applyOptimistic([id], async () => {
        await deleteMessage(id);
      });
      toast.success(t.outreach.deleted);
      setDeleteDialog(null);
    } catch {
      toast.error(t.outreach.deleteFailed);
    } finally {
      setDeleteLoading(false);
    }
  };

  // Bulk
  const toggleSelect = (id: string) => {
    setSelectedIds((s) => {
      const next = new Set(s);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };
  const clearSelection = () => setSelectedIds(new Set());

  const bulkApprove = async () => {
    if (selectedIds.size === 0) return;
    const ids = Array.from(selectedIds);
    setBulkBusy(true);
    // T8.5+++++++ Group 2: optimistic UI — remove from
    // pending tab immediately. Revert on full failure.
    let okCount = 0;
    let allFailed = false;
    await applyOptimistic(ids, async () => {
      let succeeded = 0;
      for (const id of ids) {
        try {
          await approveMessage(id, { approve: true });
          succeeded++;
        } catch {
          // Per-message failures don't roll back the
          // optimistic update — that one succeeded.
        }
      }
      okCount = succeeded;
      if (succeeded === 0) {
        allFailed = true;
        throw new Error("All approvals failed");
      }
    });
    toast.success(
      allFailed
        ? t.outreach.bulkApproveAllFailed
        : t.outreach.bulkApprovedToast
            .replace("{ok}", String(okCount))
            .replace("{total}", String(ids.length)),
    );
    clearSelection();
    setBulkBusy(false);
  };

  const bulkReject = async () => {
    if (selectedIds.size === 0) return;
    const ids = Array.from(selectedIds);
    setBulkBusy(true);
    // T8.5+++++++ Group 2 (mirror): optimistic UI for bulk
    // reject. Removes from pending tab immediately,
    // reverts on full failure.
    let okCount = 0;
    let allFailed = false;
    await applyOptimistic(ids, async () => {
      let succeeded = 0;
      for (const id of ids) {
        try {
          await approveMessage(id, { approve: false });
          succeeded++;
        } catch {
          // Per-message failures don't roll back the
          // optimistic update — that one succeeded.
        }
      }
      okCount = succeeded;
      if (succeeded === 0) {
        allFailed = true;
        throw new Error("All rejections failed");
      }
    });
    toast.success(
      allFailed
        ? t.outreach.bulkRejectAllFailed
        : t.outreach.bulkRejectedToast
            .replace("{ok}", String(okCount))
            .replace("{total}", String(ids.length)),
    );
    clearSelection();
    setBulkBusy(false);
  };

  // --- Composer ---

  const composerProspects = prospectsData?.items ?? [];
  const composerProspectOptions: ComboboxOption[] = useMemo(
    () =>
      composerProspects.map((p) => ({
        value: p.id,
        label: p.company_name,
        sublabel: p.location_city ?? p.industry ?? "",
        pill: p.quality_grade ? (
          <span
            className={cn(
              "text-[10px] font-bold px-1.5 py-0.5 rounded",
              GRADE_STYLE[p.quality_grade] ?? "bg-muted",
            )}
          >
            {p.quality_grade}
          </span>
        ) : undefined,
      })),
    [composerProspects],
  );

  const templateOptions: ComboboxOption[] = useMemo(
    () =>
      templates.map((t) => ({
        value: t.id,
        label: t.name,
        sublabel: t.category ?? t.channel,
      })),
    [templates],
  );

  const selectedComposerProspect = prospectsById[composerProspectId];

  const handleGenerate = async () => {
    if (!composerProspectId || !composerHookId) {
      toast.error(t.outreach.pickProspectHook);
      return;
    }
    setComposerLoading(true);
    try {
      const payload: MessageGenerateRequest = {
        prospect_id: composerProspectId,
        hook_id: composerHookId,
        channel: composerChannel,
        template_id: composerTemplateId || undefined,
      };
      // false = preview only (don't create draft)
      const m = await generateMessage(payload, false);
      setComposerSubject(m.subject ?? "");
      setComposerBody(m.body);
      setComposerGenerated(true);
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Generate failed");
    } finally {
      setComposerLoading(false);
    }
  };

  const handleCreateDraft = async () => {
    if (!composerGenerated || !composerProspectId || !composerHookId) {
      toast.error(t.outreach.generateFirst);
      return;
    }
    // T8.5++++++ composer inline validation
    setComposerErrors({});
    const errs: typeof composerErrors = {};
    if (composerChannel === "email" && !composerSubject.trim()) {
      errs.subject = t.outreach.subjectRequired;
    }
    if (!composerBody.trim()) {
      errs.body = t.outreach.bodyRequired;
    } else if (composerBody.trim().length < 20) {
      errs.body = t.outreach.bodyTooShort;
    }
    if (Object.keys(errs).length > 0) {
      setComposerErrors(errs);
      return;
    }
    setComposerLoading(true);
    try {
      const m = await createMessage({
        prospect_id: composerProspectId,
        channel: composerChannel,
        subject: composerSubject || "(no subject)",
        body: composerBody,
        hook_id: composerHookId,
        template_id: composerTemplateId || undefined,
      });
      toast.success(`Draft created — ${m.id.slice(0, 8)}…`);
      setComposerGenerated(false);
      setComposerSubject("");
      setComposerBody("");
      reload();
      // Auto-switch to Drafts tab + highlight new draft
      setTab("drafts");
    } catch (e) {
      toast.error(formatApiError(e));
    } finally {
      setComposerLoading(false);
    }
  };

  const handleCopyBody = async () => {
    try {
      await navigator.clipboard.writeText(composerBody);
      toast.success(t.toast.copied);
    } catch {
      toast.error(t.outreach.copyFailed);
    }
  };

  const canGenerate = !!composerProspectId && !!composerHookId && !composerLoading;
  const canSave = composerGenerated && !composerLoading;

  // --- Keyboard shortcuts ---
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement;
      const isInput =
        target.tagName === "INPUT" ||
        target.tagName === "TEXTAREA" ||
        target.isContentEditable;
      const isMod = e.metaKey || e.ctrlKey || e.altKey;
      // Cmd/Ctrl+Enter in body = save as draft
      if (isMod && e.key === "Enter" && composerGenerated) {
        e.preventDefault();
        void handleCreateDraft();
        return;
      }
      if (isInput || isMod) return;
      const k = e.key.toLowerCase();
      if (k === "a" && focusedId) {
        const m = visibleMessages.find((x) => x.id === focusedId);
        if (m?.status === "pending_approval") {
          e.preventDefault();
          void handleApprove(focusedId);
        }
      } else if (k === "r" && focusedId) {
        const m = visibleMessages.find((x) => x.id === focusedId);
        if (m?.status === "pending_approval") {
          e.preventDefault();
          handleRejectClick(focusedId);
        }
      } else if (k === "s" && focusedId) {
        const m = visibleMessages.find((x) => x.id === focusedId);
        if (m?.status === "approved" || m?.status === "failed") {
          e.preventDefault();
          void handleSend(focusedId);
        }
      } else if (k === "j" || e.key === "ArrowDown") {
        e.preventDefault();
        const idx = visibleMessages.findIndex((x) => x.id === focusedId);
        if (idx >= 0 && idx < visibleMessages.length - 1) {
          setFocusedId(visibleMessages[idx + 1].id);
        }
      } else if (k === "k" || e.key === "ArrowUp") {
        e.preventDefault();
        const idx = visibleMessages.findIndex((x) => x.id === focusedId);
        if (idx > 0) {
          setFocusedId(visibleMessages[idx - 1].id);
        }
      }
    };
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [focusedId, visibleMessages, composerGenerated]);

  // --- Tab counts (from stats) ---
  const tabCount = (t: Tab): number => {
    if (!stats) return 0;
    if (t === "pending_approval") return stats.pending_approval;
    if (t === "drafts") return stats.draft;
    if (t === "sent")
      return (
        stats.sent +
        stats.delivered +
        stats.opened +
        stats.clicked +
        stats.replied
      );
    if (t === "failed") return stats.failed + stats.bounced;
    return 0;
  };

  // --- Render ---

  return (
    <div className="space-y-5 animate-fade-in pb-24">
      {/* Header */}
      <div className="flex items-end justify-between gap-4">
        <div>
          <p className="text-xs uppercase tracking-wider text-muted-foreground font-semibold mb-1">
            {t.nav.outreach}
          </p>
          <h1 className="text-3xl font-bold tracking-tight">{t.outreach.title} — {t.outreach.pendingReview}</h1>
          <p className="text-muted-foreground mt-1.5 text-sm">
            Approve, edit, atau tolak pesan sebelum dikirim
          </p>
        </div>
      </div>

      {/* Hero stats (4 cards) */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <StatCard
          label={t.outreach.pendingReview}
          value={stats?.pending_approval ?? 0}
          icon={<Inbox className="h-4 w-4" />}
          tone="amber"
          active={tab === "pending_approval"}
          onClick={() => setTab("pending_approval")}
        />
        <StatCard
          label={t.outreach.sentTotal}
          value={
            stats
              ? stats.sent +
                stats.delivered +
                stats.opened +
                stats.clicked +
                stats.replied
              : 0
          }
          icon={<Send className="h-4 w-4" />}
          tone="emerald"
          active={tab === "sent"}
          onClick={() => setTab("sent")}
        />
        <StatCard
          label={t.outreach.replied}
          value={stats?.replied ?? 0}
          icon={<MessageSquare className="h-4 w-4" />}
          tone="sky"
        />
        <StatCard
          label={t.outreach.failed}
          value={(stats?.failed ?? 0) + (stats?.bounced ?? 0)}
          icon={<XCircle className="h-4 w-4" />}
          tone="rose"
          active={tab === "failed"}
          onClick={() => setTab("failed")}
        />
      </div>

      {/* Tabs (segmented control) + filter row */}
      <div className="flex flex-col gap-3">
        <div className="flex items-center gap-3 flex-wrap">
          {/* Segmented tabs */}
          <div className="inline-flex items-center rounded-lg border border-border bg-muted/30 p-1">
            {TABS.map((t) => {
              const isActive = tab === t.id;
              const count = tabCount(t.id);
              return (
                <button
                  key={t.id}
                  type="button"
                  onClick={() => setTab(t.id)}
                  className={cn(
                    "flex items-center gap-1.5 px-3.5 py-1.5 text-sm font-medium rounded-md transition-all duration-150 ease-out-expo",
                    isActive
                      ? "bg-background text-foreground shadow-sm"
                      : "text-muted-foreground hover:text-foreground",
                  )}
                >
                  {t.icon}
                  <span className="hidden sm:inline">{t.label}</span>
                  {count > 0 && (
                    <span
                      className={cn(
                        "inline-flex items-center justify-center min-w-5 h-5 px-1.5 rounded-full text-[10px] font-bold",
                        isActive
                          ? "bg-violet-600 text-white"
                          : "bg-muted text-muted-foreground",
                      )}
                    >
                      {count}
                    </span>
                  )}
                </button>
              );
            })}
          </div>

          {/* Search */}
          <div className="relative flex-1 min-w-[200px] max-w-md">
            <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground pointer-events-none" />
            <input
              type="search"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder={t.outreach.searchPlaceholder}
              className="w-full h-9 pl-8 pr-3 text-sm rounded-md border border-input bg-background"
            />
          </div>
        </div>

        {/* Filter chips */}
        <div className="flex items-center gap-3 flex-wrap text-sm">
          <div className="flex items-center gap-1.5 text-muted-foreground">
            <Filter className="h-3.5 w-3.5" />
            <span className="text-xs font-medium">Channel:</span>
          </div>
          <ChipGroup
            options={[
              { value: "all", label: "All" },
              { value: "email", label: t.outreach.channelEmail },
              { value: "whatsapp", label: t.outreach.channelWhatsapp },
            ]}
            value={filterChannel}
            onChange={(v) => setFilterChannel(v as FilterChannel)}
          />
          <span className="text-muted-foreground/40">|</span>
          <div className="flex items-center gap-1.5 text-muted-foreground">
            <span className="text-xs font-medium">Grade:</span>
          </div>
          <ChipGroup
            options={[
              { value: "all", label: "All" },
              { value: "A", label: "A" },
              { value: "B", label: "B" },
              { value: "C", label: "C" },
              { value: "D", label: "D" },
            ]}
            value={filterGrade}
            onChange={(v) => setFilterGrade(v as FilterGrade)}
          />
          {(filterChannel !== "all" || filterGrade !== "all" || search) && (
            <button
              type="button"
              onClick={() => {
                setFilterChannel("all");
                setFilterGrade("all");
                setSearch("");
              }}
              className="text-xs text-muted-foreground hover:text-foreground underline ml-auto"
            >
              Clear filters
            </button>
          )}
        </div>
      </div>

      {/* Main 2-col: message list (left) + composer (right) */}
      <div className="grid grid-cols-1 lg:grid-cols-[1fr_460px] gap-5">
        {/* Message list */}
        <div className="min-w-0">
          {loading ? (
            <div className="space-y-2">
              {Array.from({ length: 4 }).map((_, i) => (
                <Skeleton key={i} className="h-24" />
              ))}
            </div>
          ) : visibleMessages.length === 0 ? (
            <TabEmptyState tab={tab} search={search} />
          ) : (
            <ul className="space-y-2.5">
              {visibleMessages.map((m) => {
                const prospect = prospectsById[m.prospect_id];
                return (
                  <MessageRow
                    key={m.id}
                    message={m}
                    prospect={prospect}
                    expanded={expandedId === m.id}
                    focused={focusedId === m.id}
                    selected={selectedIds.has(m.id)}
                    busy={busyId === m.id}
                    onToggleExpand={() =>
                      setExpandedId(expandedId === m.id ? null : m.id)
                    }
                    onFocus={() => setFocusedId(m.id)}
                    onToggleSelect={() => toggleSelect(m.id)}
                    onApprove={() => handleApprove(m.id)}
                    onReject={() => handleRejectClick(m.id)}
                    onSend={() => handleSend(m.id)}
                    onSubmit={() => handleSubmit(m.id)}
                    onDelete={() => handleDeleteClick(m.id)}
                  />
                );
              })}
            </ul>
          )}
        </div>

        {/* Composer (right rail) */}
        <aside className="lg:sticky lg:top-20 lg:self-start space-y-4 lg:max-h-[calc(100vh-6rem)] lg:overflow-y-auto pr-1">
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-base flex items-center gap-2">
                <Sparkles className="h-4 w-4 text-violet-600" />
                Compose new
              </CardTitle>
              <CardDescription>
                Pick prospect + hook → AI generates message
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {/* Prospect preview card (when selected) */}
              {selectedComposerProspect && (
                <ProspectPreviewCard prospect={selectedComposerProspect} />
              )}

              {/* Step 1: Prospect combobox */}
              <div className="space-y-1.5">
                <label className="text-sm font-medium text-foreground">
                  1. Prospect
                </label>
                <Combobox
                  options={composerProspectOptions}
                  value={composerProspectId}
                  onChange={setComposerProspectId}
                  placeholder={t.outreach.searchProspectPlaceholder}
                  emptyMessage={t.outreach.noProspectsMatch}
                  size="sm"
                />
              </div>

              {/* Step 2: Hook cards */}
              {composerProspectId && (
                <div className="space-y-1.5">
                  <label className="text-sm font-medium text-foreground">
                    2. Hook
                  </label>
                  {prospectHooks.length === 0 ? (
                    <div className="p-3 rounded-lg border border-amber-200 bg-amber-50/50">
                      <p className="text-xs text-amber-800">
                        No hooks yet. Generate them on the prospect detail
                        page first.
                      </p>
                      <Button
                        size="sm"
                        variant="outline"
                        asChild
                        className="mt-2"
                      >
                        <Link to={`/prospects/${composerProspectId}`}>
                          Open prospect
                        </Link>
                      </Button>
                    </div>
                  ) : (
                    <ul className="space-y-2">
                      {prospectHooks.map((h) => (
                        <HookCard
                          key={h.id}
                          hook={h}
                          selected={composerHookId === h.id}
                          onSelect={() => setComposerHookId(h.id)}
                        />
                      ))}
                    </ul>
                  )}
                </div>
              )}

              {/* Step 3: Channel */}
              <div className="space-y-1.5">
                <label className="text-sm font-medium text-foreground">
                  3. Channel
                </label>
                <div className="grid grid-cols-2 gap-1.5">
                  {(["email", "whatsapp"] as MessageChannel[]).map((c) => (
                    <button
                      key={c}
                      type="button"
                      onClick={() => setComposerChannel(c)}
                      className={cn(
                        "h-8 rounded-md text-sm font-medium border transition-colors flex items-center justify-center gap-1.5",
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
                      <span className="capitalize">{c}</span>
                    </button>
                  ))}
                </div>
              </div>

              {/* Step 4: Optional template override */}
              {templateOptions.length > 0 && (
                <div className="space-y-1.5">
                  <label className="text-sm font-medium text-foreground">
                    4. Template{" "}
                    <span className="text-xs text-muted-foreground font-normal">
                      (opsional)
                    </span>
                  </label>
                  <Combobox
                    options={templateOptions}
                    value={composerTemplateId}
                    onChange={setComposerTemplateId}
                    placeholder={t.outreach.templatePlaceholder}
                    emptyMessage={t.outreach.noTemplates}
                    size="sm"
                  />
                </div>
              )}

              {/* Generate CTA */}
              <Button
                onClick={handleGenerate}
                disabled={!canGenerate}
                className="w-full"
                size="lg"
              >
                {composerLoading ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Sparkles className="h-4 w-4" />
                )}
                Generate with AI
              </Button>
              {canGenerate && !composerGenerated && (
                <p className="text-xs text-muted-foreground text-center -mt-2">
                  ~5s · uses your selected hook + prospect data
                </p>
              )}

              {/* Generated preview (editable) */}
              {composerGenerated && (
                <div className="p-3 rounded-lg border-2 border-violet-300 bg-violet-50/30 dark:bg-violet-950/20 space-y-3 animate-fade-in">
                  <div className="flex items-center gap-2">
                    <Sparkles className="h-3.5 w-3.5 text-violet-600" />
                    <span className="text-xs font-medium text-violet-700">
                      AI generated · edit before saving
                    </span>
                  </div>
                  {composerChannel === "email" && (
                    <FormField
                      label="Subjek"
                      required
                      hint="Wajib diisi sebelum menyimpan"
                      error={composerErrors.subject}
                    >
                      <Input
                        value={composerSubject}
                        onChange={(e) => setComposerSubject(e.target.value)}
                        className="h-8 text-sm"
                      />
                    </FormField>
                  )}
                  <FormField
                    label="Body"
                    required
                    hint="Wajib diisi sebelum menyimpan"
                    error={composerErrors.body}
                  >
                    <Textarea
                      value={composerBody}
                      onChange={(e) => setComposerBody(e.target.value)}
                      rows={8}
                      className="resize-none"
                    />
                  </FormField>
                  <div className="flex items-center gap-2">
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={handleCopyBody}
                    >
                      <Copy className="h-3.5 w-3.5" />
                      Copy
                    </Button>
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={handleGenerate}
                      disabled={composerLoading}
                    >
                      <RotateCcw className="h-3.5 w-3.5" />
                      Regenerate
                    </Button>
                    <Button
                      size="sm"
                      onClick={handleCreateDraft}
                      disabled={!canSave}
                      className="ml-auto"
                    >
                      <Plus className="h-3.5 w-3.5" />
                      Save as draft
                    </Button>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        </aside>
      </div>

      {/* Bulk action bar (sticky bottom) */}
      {selectedIds.size > 0 && (
        <div className="fixed bottom-0 left-0 right-0 z-30 pointer-events-none">
          <div className="max-w-7xl mx-auto px-6 pb-6 pointer-events-none">
            <div className="ml-0 md:ml-60 pointer-events-auto">
              <div className="flex items-center justify-between gap-3 p-3 rounded-xl border border-border bg-card shadow-2xl animate-fade-in">
                <span className="text-sm font-medium pl-2">
                  {selectedIds.size} selected
                </span>
                <div className="flex items-center gap-2">
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={clearSelection}
                    disabled={bulkBusy}
                  >
                    Cancel
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={bulkReject}
                    disabled={bulkBusy}
                    className="text-rose-600 hover:text-rose-700"
                  >
                    <XCircle className="h-3.5 w-3.5" />
                    Reject all
                  </Button>
                  <Button
                    size="sm"
                    onClick={bulkApprove}
                    disabled={bulkBusy}
                  >
                    {bulkBusy ? (
                      <Loader2 className="h-3.5 w-3.5 animate-spin" />
                    ) : (
                      <CheckCircle2 className="h-3.5 w-3.5" />
                    )}
                    Approve all
                  </Button>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Confirm dialogs */}
      <ConfirmDialog
        open={rejectDialog !== null}
        onOpenChange={(o) => !o && setRejectDialog(null)}
        title={t.outreach.rejectTitle}
        description={t.outreach.rejectDescription}
        input={{
          label: t.outreach.reasonOptional,
          placeholder: "Too salesy, wrong tone, etc.",
          value: rejectDialog?.reason ?? "",
          onChange: (v) =>
            setRejectDialog((d) => (d ? { ...d, reason: v } : d)),
        }}
        confirmText="Reject"
        destructive
        loading={rejectLoading}
        onConfirm={handleRejectConfirm}
      />
      <ConfirmDialog
        open={deleteDialog !== null}
        onOpenChange={(o) => !o && setDeleteDialog(null)}
        title="Delete this message?"
        description="This action cannot be undone. The message will be permanently removed from the queue."
        confirmText="Delete"
        destructive
        loading={deleteLoading}
        onConfirm={handleDeleteConfirm}
      />
    </div>
  );
}

// --- Sub-components ---

function StatCard({
  label,
  value,
  icon,
  tone,
  active = false,
  onClick,
}: {
  label: string;
  value: number;
  icon: React.ReactNode;
  tone: "amber" | "emerald" | "sky" | "rose";
  active?: boolean;
  onClick?: () => void;
}) {
  const toneClass = {
    amber: "text-amber-600 bg-amber-50 dark:bg-amber-950/30",
    emerald: "text-emerald-600 bg-emerald-50 dark:bg-emerald-950/30",
    sky: "text-sky-600 bg-sky-50 dark:bg-sky-950/30",
    rose: "text-rose-600 bg-rose-50 dark:bg-rose-950/30",
  }[tone];
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={!onClick}
      className={cn(
        "p-4 rounded-xl border bg-card text-left transition-all",
        active
          ? "border-violet-500 ring-1 ring-violet-500"
          : "border-border hover:border-violet-300",
        onClick && "cursor-pointer",
      )}
    >
      <div className="flex items-center justify-between mb-2">
        <span className="text-xs uppercase tracking-wider text-muted-foreground font-semibold">
          {label}
        </span>
        <div className={cn("h-7 w-7 rounded-lg flex items-center justify-center", toneClass)}>
          {icon}
        </div>
      </div>
      <p className="text-2xl font-bold tracking-tight num">{value}</p>
    </button>
  );
}

function ChipGroup<T extends string>({
  options,
  value,
  onChange,
}: {
  options: { value: T; label: string }[];
  value: T;
  onChange: (v: T) => void;
}) {
  return (
    <div className="inline-flex items-center gap-0.5 rounded-full border border-border bg-muted/30 p-0.5">
      {options.map((o) => {
        const isActive = value === o.value;
        return (
          <button
            key={o.value}
            type="button"
            onClick={() => onChange(o.value)}
            className={cn(
              "px-2.5 py-0.5 text-xs font-medium rounded-full transition-colors",
              isActive
                ? "bg-background text-foreground shadow-sm"
                : "text-muted-foreground hover:text-foreground",
            )}
          >
            {o.label}
          </button>
        );
      })}
    </div>
  );
}

function ProspectPreviewCard({ prospect }: { prospect: Prospect }) {
  return (
    <Link
      to={`/prospects/${prospect.id}`}
      className="block p-3 rounded-lg border border-border bg-muted/30 hover:border-violet-300 transition-colors"
    >
      <div className="flex items-center gap-3">
        <div className="h-10 w-10 rounded-md bg-gradient-to-br from-violet-500 to-indigo-600 text-white flex items-center justify-center font-semibold text-sm flex-shrink-0">
          {getInitials(prospect.company_name)}
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-1.5 flex-wrap">
            <p className="text-sm font-semibold truncate">
              {prospect.company_name}
            </p>
            {prospect.quality_grade && (
              <span
                className={cn(
                  "text-[10px] font-bold px-1.5 py-0.5 rounded",
                  GRADE_STYLE[prospect.quality_grade] ?? "bg-muted",
                )}
              >
                {prospect.quality_grade}
              </span>
            )}
            {prospect.score_total != null && (
              <span className="text-xs text-muted-foreground">
                · {prospect.score_total}/100
              </span>
            )}
          </div>
          <p className="text-xs text-muted-foreground truncate mt-0.5">
            {[prospect.industry, prospect.location_city]
              .filter(Boolean)
              .join(" · ")}
          </p>
        </div>
        <ChevronRight className="h-4 w-4 text-muted-foreground flex-shrink-0" />
      </div>
    </Link>
  );
}

function HookCard({
  hook,
  selected,
  onSelect,
}: {
  hook: { id: string; hook_text: string; recommended_service: string | null; confidence: number };
  selected: boolean;
  onSelect: () => void;
}) {
  return (
    <li>
      <button
        type="button"
        onClick={onSelect}
        className={cn(
          "w-full text-left p-2.5 rounded-lg border-2 transition-all",
          selected
            ? "border-violet-500 bg-violet-50/50 dark:bg-violet-950/30"
            : "border-border bg-card hover:border-violet-300",
        )}
      >
        <div className="flex items-start gap-2">
          <div
            className={cn(
              "h-4 w-4 rounded-full flex-shrink-0 mt-0.5 flex items-center justify-center",
              selected ? "bg-violet-600" : "border-2 border-muted-foreground/40",
            )}
          >
            {selected && <Check className="h-2.5 w-2.5 text-white" />}
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-1.5 mb-1 flex-wrap">
              {hook.recommended_service && (
                <span className="text-[10px] font-bold uppercase tracking-wider px-1.5 py-0.5 rounded bg-violet-100 text-violet-800">
                  {hook.recommended_service}
                </span>
              )}
              <span className="text-xs text-muted-foreground">
                {Math.round((hook.confidence ?? 0.5) * 100)}% conf
              </span>
            </div>
            <p className="text-xs leading-relaxed line-clamp-3">{hook.hook_text}</p>
          </div>
        </div>
      </button>
    </li>
  );
}

interface MessageRowProps {
  message: Message;
  prospect?: Prospect;
  expanded: boolean;
  focused: boolean;
  selected: boolean;
  busy: boolean;
  onToggleExpand: () => void;
  onFocus: () => void;
  onToggleSelect: () => void;
  onApprove: () => void;
  onReject: () => void;
  onSend: () => void;
  onSubmit: () => void;
  onDelete: () => void;
}

function MessageRow({
  message: m,
  prospect,
  expanded,
  focused,
  selected,
  busy,
  onToggleExpand,
  onFocus,
  onToggleSelect,
  onApprove,
  onReject,
  onSend,
  onSubmit,
  onDelete,
}: MessageRowProps) {
  const ch = CHANNEL_STYLE[m.channel] ?? CHANNEL_STYLE.email;
  const statusBadge = STATUS_BADGE[m.status] ?? STATUS_BADGE.draft;

  return (
    <li
      onClick={onFocus}
      className={cn(
        "rounded-xl border bg-card overflow-hidden transition-all",
        focused
          ? "border-violet-400 ring-1 ring-violet-400 shadow-sm"
          : "border-border",
        selected && "bg-violet-50/30 dark:bg-violet-950/20",
      )}
    >
      {/* Header row — always visible, inline actions */}
      <div className="p-3.5 flex items-start gap-3">
        {/* Bulk checkbox */}
        <input
          type="checkbox"
          checked={selected}
          onChange={onToggleSelect}
          onClick={(e) => e.stopPropagation()}
          className="mt-1 h-4 w-4 rounded border-input text-violet-600 focus:ring-violet-500 flex-shrink-0"
        />

        {/* Channel icon in colored circle */}
        <div
          className={cn(
            "h-9 w-9 rounded-lg flex items-center justify-center flex-shrink-0",
            ch.bg,
            ch.text,
          )}
        >
          {ch.icon}
        </div>

        {/* Main content (clickable to expand) */}
        <button
          type="button"
          onClick={onToggleExpand}
          className="flex-1 min-w-0 text-left"
        >
          {/* Top: company + grade + score + status badge + time */}
          <div className="flex items-center gap-1.5 flex-wrap mb-1">
            {prospect ? (
              <>
                <span className="text-sm font-semibold text-foreground truncate max-w-[200px]">
                  {prospect.company_name}
                </span>
                {prospect.quality_grade && (
                  <span
                    className={cn(
                      "text-[10px] font-bold px-1.5 py-0.5 rounded uppercase",
                      GRADE_STYLE[prospect.quality_grade] ?? "bg-muted",
                    )}
                  >
                    {prospect.quality_grade}
                  </span>
                )}
                {prospect.score_total != null && (
                  <span className="text-xs text-muted-foreground num tabular-nums">
                    · {prospect.score_total}
                  </span>
                )}
              </>
            ) : (
              <span className="text-sm font-medium text-muted-foreground italic">
                Loading prospect…
              </span>
            )}
            <span
              className={cn(
                "inline-flex items-center gap-1 text-[10px] font-bold uppercase tracking-wider px-1.5 py-0.5 rounded",
                statusBadge.bg,
              )}
            >
              <span className="h-1.5 w-1.5 rounded-full bg-current opacity-60" />
              {m.status.replace("_", " ")}
            </span>
            <span className="text-xs text-muted-foreground ml-auto">
              {formatRelativeId(m.created_at)}
            </span>
          </div>
          <p className="text-sm font-medium truncate">
            {m.subject || m.body.slice(0, 80) || "(no subject)"}
          </p>
          <p className="text-xs text-muted-foreground mt-0.5 line-clamp-2">
            {m.body.slice(0, 200)}
          </p>
        </button>

        {/* Inline primary actions */}
        <div className="flex items-center gap-1.5 flex-shrink-0">
          {m.status === "pending_approval" && (
            <>
              <Button
                size="sm"
                onClick={(e) => {
                  e.stopPropagation();
                  onApprove();
                }}
                disabled={busy}
                title="Approve (A)"
              >
                <CheckCircle2 className="h-3.5 w-3.5" />
                <span className="hidden lg:inline">Approve</span>
              </Button>
              <Button
                size="sm"
                variant="outline"
                onClick={(e) => {
                  e.stopPropagation();
                  onReject();
                }}
                disabled={busy}
                title="Reject (R)"
              >
                <XCircle className="h-3.5 w-3.5" />
              </Button>
            </>
          )}
          {m.status === "approved" && (
            <Button
              size="sm"
              onClick={(e) => {
                e.stopPropagation();
                onSend();
              }}
              disabled={busy}
              title="Send now (S)"
            >
              <Send className="h-3.5 w-3.5" />
              <span className="hidden lg:inline">Send</span>
            </Button>
          )}
          {m.status === "draft" && (
            <Button
              size="sm"
              onClick={(e) => {
                e.stopPropagation();
                onSubmit();
              }}
              disabled={busy}
              title="Submit for approval"
            >
              <Inbox className="h-3.5 w-3.5" />
              <span className="hidden lg:inline">Submit</span>
            </Button>
          )}
          {(m.status === "failed" || m.status === "bounced") && (
            <Button
              size="sm"
              onClick={(e) => {
                e.stopPropagation();
                onSend();
              }}
              disabled={busy}
              title="Retry send"
            >
              <RotateCcw className="h-3.5 w-3.5" />
              <span className="hidden lg:inline">Retry</span>
            </Button>
          )}
          <Button
            size="icon"
            variant="ghost"
            onClick={(e) => {
              e.stopPropagation();
              onToggleExpand();
            }}
            className="h-7 w-7"
            title={expanded ? "Collapse" : "Show more"}
          >
            <ChevronDown
              className={cn(
                "h-4 w-4 transition-transform",
                expanded && "rotate-180",
              )}
            />
          </Button>
        </div>
      </div>

      {/* Expanded details */}
      {expanded && (
        <div className="border-t border-border bg-muted/20 p-4 space-y-3">
          {m.subject && (
            <div className="space-y-1">
              <p className="text-[10px] uppercase tracking-wider text-muted-foreground font-semibold">
                Subject
              </p>
              <p className="text-sm font-medium">{m.subject}</p>
            </div>
          )}
          <div className="space-y-1">
            <p className="text-[10px] uppercase tracking-wider text-muted-foreground font-semibold">
              Body
            </p>
            <pre className="text-sm leading-relaxed whitespace-pre-wrap max-h-96 overflow-y-auto p-3 rounded-md bg-card border border-border font-sans">
              {m.body}
            </pre>
          </div>

          {/* Delivery progress (D5) */}
          {DELIVERY_FUNNEL.includes(m.status) && (
            <DeliveryProgress status={m.status} />
          )}

          {m.error_message && (
            <div className="p-3 rounded-md bg-rose-50 dark:bg-rose-950/30 border border-rose-200">
              <div className="flex items-start gap-2">
                <AlertTriangle className="h-3.5 w-3.5 text-rose-600 flex-shrink-0 mt-0.5" />
                <p className="text-xs text-rose-700 font-mono break-all">
                  {m.error_message}
                </p>
              </div>
            </div>
          )}

          <div className="flex flex-wrap items-center gap-2 pt-1">
            {(m.status === "draft" ||
              m.status === "pending_approval" ||
              m.status === "rejected" ||
              m.status === "failed" ||
              m.status === "bounced") && (
              <Button
                size="sm"
                variant="ghost"
                onClick={(e) => {
                  e.stopPropagation();
                  onDelete();
                }}
                disabled={busy}
                className="text-rose-600 hover:text-rose-700"
              >
                <Trash2 className="h-3.5 w-3.5" />
                Delete
              </Button>
            )}
            <span className="text-xs text-muted-foreground ml-auto">
              {m.sent_at && `Sent ${formatTimeShort(m.sent_at)}`}
              {m.approved_at && !m.sent_at && `Approved ${formatTimeShort(m.approved_at)}`}
            </span>
          </div>
        </div>
      )}
    </li>
  );
}

function DeliveryProgress({ status }: { status: string }) {
  const reachedIdx = DELIVERY_FUNNEL.indexOf(status);
  return (
    <div>
      <p className="text-[10px] uppercase tracking-wider text-muted-foreground font-semibold mb-1.5">
        Delivery progress
      </p>
      <div className="flex items-center gap-1.5">
        {DELIVERY_FUNNEL.map((s, i) => {
          const reached = i <= reachedIdx;
          return (
            <div key={s} className="flex items-center gap-1.5 flex-1">
              <div
                className={cn(
                  "h-2 flex-1 rounded-full transition-colors",
                  reached ? "bg-emerald-500" : "bg-muted",
                )}
              />
            </div>
          );
        })}
      </div>
      <div className="flex items-center justify-between mt-1.5 text-[10px] text-muted-foreground">
        {DELIVERY_FUNNEL.map((s) => (
          <span
            key={s}
            className={cn(
              "uppercase tracking-wider",
              DELIVERY_FUNNEL.indexOf(status) >= DELIVERY_FUNNEL.indexOf(s)
                ? "text-emerald-700 font-semibold"
                : "text-muted-foreground/60",
            )}
          >
            {s.slice(0, 3)}
          </span>
        ))}
      </div>
    </div>
  );
}

function TabEmptyState({ tab, search }: { tab: Tab; search: string }) {
  if (search) {
    return (
      <EmptyState
        className="py-12"
        icon={<Search className="h-5 w-5" />}
        title="No results"
        description={`Nothing matches "${search}". Try a different search or clear the filter.`}
      />
    );
  }
  if (tab === "pending_approval") {
    return (
      <EmptyState
        className="py-12"
        icon={
          <div className="h-12 w-12 rounded-full bg-emerald-100 dark:bg-emerald-950/30 flex items-center justify-center">
            <CheckCircle2 className="h-6 w-6 text-emerald-600" />
          </div>
        }
        title="All caught up"
        description="No messages waiting for review. Inbound messages will appear here when generated."
      />
    );
  }
  if (tab === "drafts") {
    return (
      <EmptyState
        className="py-12"
        icon={<Sparkles className="h-5 w-5 text-violet-500" />}
        title="No drafts yet"
        description="Use the composer on the right → to create a draft from a prospect's hook."
      />
    );
  }
  if (tab === "sent") {
    return (
      <EmptyState
        className="py-12"
        icon={<Send className="h-5 w-5 text-emerald-500" />}
        title="Nothing sent yet"
        description="Approved messages you send will show here with delivery status."
      />
    );
  }
  return (
    <EmptyState
      className="py-12"
      icon={
        <div className="h-12 w-12 rounded-full bg-rose-100 dark:bg-rose-950/30 flex items-center justify-center">
          <XCircle className="h-6 w-6 text-rose-600" />
        </div>
      }
      title="No failures"
      description="Nothing failed to send. (If you see failures, check SMTP/WAHA config.)"
    />
  );
}

// --- helpers ---

// (Token handling is done by the axios `api` client via interceptors,
// so direct fetch() calls aren't needed here.)
