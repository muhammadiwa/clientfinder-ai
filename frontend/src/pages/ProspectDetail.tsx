import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import {
  ArrowLeft,
  Sparkles,
  RefreshCw,
  Copy,
  Check,
  ExternalLink,
  Globe,
  MapPin,
  Phone,
  Mail,
  Building2,
  Activity,
  AlertTriangle,
  Tag,
  Clock,
  Server,
  Zap,
  MessageSquare,
  TrendingUp,
  CheckCircle2,
} from "lucide-react";
import { toast } from "react-hot-toast";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/ui/empty-state";
import { StatusPill, GradePill } from "@/components/ui/status-pill";
import { TierBadge } from "@/components/TierBadge";
import { ScoreBreakdownChart } from "@/components/charts/ScoreBreakdown";
import { SignalList } from "@/components/SignalList";
import { EnrollmentPanel } from "@/components/EnrollmentPanel";
import { ScoutRunBreadcrumb } from "@/components/ScoutRunBreadcrumb";
import {
  classifyProspect,
  enrichProspect,
  getProspectDetail,
  refreshContact,
  type ClassifyResult,
  type ProspectDetailResponse,
  type Tier,
} from "@/api/prospects";
import { generateHooks } from "@/services/ai/ai-analyzer";
import { cn } from "@/lib/utils";
import { useT } from "@/i18n";

/**
 * ProspectDetail — full analyst view (T5 Group 3).
 *
 * Hero: company identity + grade + total score
 * Body:
 *   - Score breakdown (5-factor chart)
 *   - Tech stack audit
 *   - Pain points (heuristic + LLM)
 *   - AI-generated outreach hooks
 * Actions:
 *   - Re-analyze (POST /enrich)
 *   - Generate hooks (calls /ai/hooks)
 *   - Copy hook to clipboard
 */
export function ProspectDetailPage() {
  const t = useT();
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const [detail, setDetail] = useState<ProspectDetailResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [analyzing, setAnalyzing] = useState(false);
  const [generatingHooks, setGeneratingHooks] = useState(false);
  const [refreshingContact, setRefreshingContact] = useState(false);
  const [classifying, setClassifying] = useState(false);
  const [classifyResult, setClassifyResult] = useState<ClassifyResult | null>(
    null,
  );
  const [copiedHookId, setCopiedHookId] = useState<string | null>(null);

  const fetchDetail = async () => {
    if (!id) return;
    setLoading(true);
    setError(null);
    try {
      const data = await getProspectDetail(id);
      setDetail(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : t.prospectDetail.failedToLoadDetail);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDetail();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  const handleReanalyze = async () => {
    if (!id) return;
    setAnalyzing(true);
    try {
      const result = await enrichProspect(id);
      if (result.ok) {
        toast.success(
          `Re-analyzed: ${result.grade ?? "?"} (${result.total_score ?? 0})`,
        );
        await fetchDetail();
      } else {
        toast.error(result.error ?? t.prospectDetail.reAnalyzeFailed);
      }
    } catch (e) {
      toast.error(e instanceof Error ? e.message : t.prospectDetail.reAnalyzeFailed);
    } finally {
      setAnalyzing(false);
    }
  };

  const handleGenerateHooks = async () => {
    if (!id) return;
    setGeneratingHooks(true);
    try {
      const result = await generateHooks(id);
      if (result.ok) {
        toast.success(
          `Generated ${result.hooks.length} hooks via ${result.source}`,
        );
        await fetchDetail();
      } else {
        toast.error(result.error ?? t.prospectDetail.hookGenFailed);
      }
    } finally {
      setGeneratingHooks(false);
    }
  };

  // Sprint 3B — tier + industry classification
  const handleClassify = async () => {
    if (!id) return;
    setClassifying(true);
    try {
      const result = await classifyProspect(id);
      setClassifyResult(result);
      toast.success(
        `Tier: ${result.tier} (${Math.round(result.tier_confidence * 100)}% confident)`,
      );
      // Re-fetch to get the updated description (with industry prefix)
      await fetchDetail();
    } catch (e: unknown) {
      toast.error(
        (e as Error)?.message ?? t.prospectDetail.classifyFailed,
      );
    } finally {
      setClassifying(false);
    }
  };

  const handleCopyHook = async (text: string, hookId: string) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopiedHookId(hookId);
      toast.success(t.prospectDetail.hookCopied);
      setTimeout(() => setCopiedHookId(null), 2000);
    } catch {
      toast.error(t.prospectDetail.copyFailed);
    }
  };

  // T8.6: re-fetch the prospect's homepage and extract phone, email,
  // address, and social links. Best-effort: errors are surfaced via
  // toast, the detail re-fetch shows the updated fields on success.
  const handleRefreshContact = async () => {
    if (!id) return;
    if (refreshingContact) return;
    setRefreshingContact(true);
    try {
      const result = await refreshContact(id);
      if (result.status === "ok") {
        const found: string[] = [];
        if (result.fields.phone) found.push("phone");
        if (result.fields.email) found.push("email");
        if (result.fields.address) found.push("address");
        if (Object.keys(result.fields.socials).length > 0) found.push("socials");
        toast.success(
          found.length > 0
            ? `Kontak diperbarui: ${found.join(", ")}`
            : "Halaman berhasil dimuat, tapi tidak ada info kontak yang ditemukan",
        );
      } else if (result.status === "no_data") {
        toast("Halaman dimuat, tapi tidak ada info kontak publik", { icon: "ℹ️" });
      } else if (result.status === "timeout") {
        toast.error("Timeout saat memuat halaman");
      } else {
        toast.error("Gagal memperbarui kontak");
      }
      // Re-fetch detail so the UI shows the updated fields
      await fetchDetail();
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Gagal memperbarui kontak";
      toast.error(msg);
    } finally {
      setRefreshingContact(false);
    }
  };

  if (loading && !detail) {
    return <DetailSkeleton />;
  }

  if (error || !detail) {
    return (
      <div className="space-y-6">
        <Button variant="ghost" onClick={() => navigate("/prospects")}>
          <ArrowLeft className="h-4 w-4" />
          Back to prospects
        </Button>
        <EmptyState
          icon={<AlertTriangle className="h-5 w-5" />}
          title={t.prospectDetail.couldNotLoad}
          description={error ?? t.prospectDetail.notFound}
          action={
            <Button onClick={fetchDetail}>
              <RefreshCw className="h-4 w-4" />
              Try again
            </Button>
          }
        />
      </div>
    );
  }

  const {
    prospect,
    tech_stack,
    pain_points,
    lead_score,
    hooks,
    signals,
    scout_run_id: scoutRunId,
  } = detail;
  const hasScore = lead_score != null;

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Sprint 4 PR 3: breadcrumb linking back to the ScoutRun
          that found this prospect. Layer 1 of the hybrid C display
          — small, clean, deep-linkable. */}
      <ScoutRunBreadcrumb scoutRunId={scoutRunId} />

      {/* Top bar */}
      <div className="flex items-center justify-between gap-4">
        <Button
          variant="ghost"
          size="sm"
          onClick={() => navigate("/prospects")}
        >
          <ArrowLeft className="h-4 w-4" />
          Back to prospects
        </Button>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={handleClassify}
            disabled={classifying}
            data-testid="classify-button"
            title={t.prospectDetail.classifyTitle ?? "Sprint 3B: tier + industry"}
          >
            {classifying ? (
              <RefreshCw className="h-4 w-4 animate-spin" />
            ) : (
              <Building2 className="h-4 w-4" />
            )}
            {t.prospectDetail.classify}
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={handleReanalyze}
            disabled={analyzing}
          >
            {analyzing ? (
              <RefreshCw className="h-4 w-4 animate-spin" />
            ) : (
              <RefreshCw className="h-4 w-4" />
            )}
            Re-analyze
          </Button>
          {hasScore && (
            <span className="hidden sm:inline-flex items-center gap-1.5 text-xs text-muted-foreground">
              <Clock className="h-3 w-3" />
              Scored {formatRelative(lead_score.scored_at)}
            </span>
          )}
        </div>
      </div>

      {/* Hero card */}
      <Card>
        <CardContent className="p-6">
          <div className="flex flex-col md:flex-row md:items-start md:justify-between gap-6">
            <div className="flex-1 min-w-0 space-y-3">
              <div className="flex items-center gap-2 flex-wrap">
                <h1 className="text-2xl md:text-3xl font-bold tracking-tight">
                  {prospect.company_name}
                </h1>
                {prospect.quality_grade && (
                  <GradePill grade={prospect.quality_grade} />
                )}
                <TierBadge
                  tier={
                    (classifyResult?.tier ?? prospect.tier ?? null) as Tier | null
                  }
                  confidence={
                    (classifyResult?.tier_confidence
                      ?? prospect.tier_confidence
                      ?? undefined) as number | undefined
                  }
                />
                <StatusPill status={prospect.status} />
              </div>
              <div className="flex flex-wrap items-center gap-x-4 gap-y-1.5 text-sm text-muted-foreground">
                {prospect.industry && (
                  <span className="inline-flex items-center gap-1.5">
                    <Tag className="h-3.5 w-3.5" />
                    <span className="capitalize">{prospect.industry}</span>
                    {classifyResult?.industry_specific &&
                      classifyResult.industry_specific !== "unknown" && (
                      <span
                        data-testid="industry-specific"
                        className="ml-1 text-xs text-violet-600 dark:text-violet-400"
                      >
                        → {classifyResult.industry_specific}
                      </span>
                    )}
                  </span>
                )}
                {prospect.location_city && (
                  <span className="inline-flex items-center gap-1.5">
                    <MapPin className="h-3.5 w-3.5" />
                    {prospect.location_city}
                  </span>
                )}
                {prospect.phone && (
                  <a
                    href={`tel:${prospect.phone}`}
                    className="inline-flex items-center gap-1.5 hover:text-foreground"
                  >
                    <Phone className="h-3.5 w-3.5" />
                    {prospect.phone}
                  </a>
                )}
                {prospect.email && (
                  <a
                    href={`mailto:${prospect.email}`}
                    className="inline-flex items-center gap-1.5 hover:text-foreground"
                  >
                    <Mail className="h-3.5 w-3.5" />
                    {prospect.email}
                  </a>
                )}
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={handleRefreshContact}
                  disabled={refreshingContact || !prospect.website}
                  className="h-7 px-2 text-xs"
                  title={
                    prospect.website
                      ? "Fetch homepage untuk update phone/email/address/socials"
                      : "Tidak ada website untuk di-fetch"
                  }
                >
                  <RefreshCw
                    className={cn(
                      "h-3 w-3",
                      refreshingContact && "animate-spin",
                    )}
                  />
                  {refreshingContact ? "Memperbarui…" : "Refresh kontak"}
                </Button>
              </div>
              {prospect.description && (
                <p className="text-sm text-muted-foreground leading-relaxed max-w-3xl mt-2">
                  {prospect.description}
                </p>
              )}
              {prospect.website && (
                <a
                  href={prospect.website}
                  target="_blank"
                  rel="noreferrer"
                  className="inline-flex items-center gap-1.5 text-sm text-violet-600 hover:text-violet-700"
                >
                  <Globe className="h-3.5 w-3.5" />
                  {truncateUrl(prospect.website, 50)}
                  <ExternalLink className="h-3 w-3" />
                </a>
              )}
            </div>

            {/* Right side: source + meta */}
            <div className="flex flex-col items-end gap-1 text-xs text-muted-foreground">
              <div className="flex items-center gap-1.5">
                <Building2 className="h-3.5 w-3.5" />
                <span className="capitalize">{prospect.source}</span>
              </div>
              <div className="flex items-center gap-1.5">
                <Clock className="h-3.5 w-3.5" />
                Discovered {formatRelative(prospect.discovered_at)}
              </div>
              {prospect.score_total != null && (
                <div className="flex items-center gap-1.5">
                  <TrendingUp className="h-3.5 w-3.5" />
                  Score {prospect.score_total}/100
                </div>
              )}
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Business context (Sprint 1 / T5 v3 / brief: 4 extra fields) */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg flex items-center gap-2">
            <Building2 className="h-4 w-4 text-muted-foreground" />
            {t.prospectDetail.ownerName} &amp; bisnis
          </CardTitle>
          <CardDescription>
            Konteks bisnis singkat (brief: nama owner, jumlah karyawan,
            estimasi revenue, peluang closing)
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="space-y-1">
              <div className="text-xs uppercase tracking-wider text-muted-foreground font-medium">
                {t.prospectDetail.ownerName}
              </div>
              <div className="text-sm font-medium">
                {prospect.owner_name || (
                  <span className="text-muted-foreground italic">
                    {t.prospectDetail.ownerUnknown}
                  </span>
                )}
              </div>
            </div>
            <div className="space-y-1">
              <div className="text-xs uppercase tracking-wider text-muted-foreground font-medium">
                {t.prospectDetail.employeeCount}
              </div>
              <div className="text-sm font-medium num">
                {prospect.employee_count != null
                  ? `${prospect.employee_count} ${t.prospectDetail.employeesUnit}`
                  : (
                      <span className="text-muted-foreground italic">
                        {t.prospectDetail.ownerUnknown}
                      </span>
                    )}
              </div>
            </div>
            <div className="space-y-1">
              <div className="text-xs uppercase tracking-wider text-muted-foreground font-medium">
                {t.prospectDetail.revenueEstimate}
              </div>
              <div className="text-sm font-medium">
                {prospect.revenue_estimate || (
                  <span className="text-muted-foreground italic">
                    {t.prospectDetail.ownerUnknown}
                  </span>
                )}
              </div>
            </div>
            <div className="space-y-1">
              <div className="text-xs uppercase tracking-wider text-muted-foreground font-medium">
                {t.prospectDetail.closingProbability}
              </div>
              <div className="text-sm font-medium num">
                {prospect.closing_probability != null
                  ? `${prospect.closing_probability}${t.prospectDetail.closingPercent}`
                  : (
                      <span className="text-muted-foreground italic">
                        {t.prospectDetail.ownerUnknown}
                      </span>
                    )}
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Score breakdown */}
      {hasScore ? (
        <Card>
          <CardHeader>
            <CardTitle className="text-lg flex items-center gap-2">
              <Activity className="h-4 w-4 text-muted-foreground" />
              Score breakdown
            </CardTitle>
            <CardDescription>
              7-factor weighted scoring + risk penalty (Sprint 1 / T5 v3)
            </CardDescription>
          </CardHeader>
          <CardContent>
            <ScoreBreakdownChart
              factors={[
                {
                  key: "pain_severity",
                  label: t.prospectDetail.factors.painSeverity,
                  value: lead_score!.pain_severity,
                  description: t.prospectDetail.factors.painSeverityDesc,
                },
                {
                  key: "solution_fit",
                  label: t.prospectDetail.factors.solutionFit,
                  value: lead_score!.solution_fit,
                  description: t.prospectDetail.factors.solutionFitDesc,
                },
                {
                  key: "signal_strength",
                  label: t.prospectDetail.factors.signalStrength,
                  value: lead_score!.signal_strength,
                  description: t.prospectDetail.factors.signalStrengthDesc,
                },
                {
                  key: "budget_indicator",
                  label: t.prospectDetail.factors.budgetIndicator,
                  value: lead_score!.budget_indicator,
                  description: t.prospectDetail.factors.budgetIndicatorDesc,
                },
                {
                  key: "timing_urgency",
                  label: t.prospectDetail.factors.timingUrgency,
                  value: lead_score!.timing_urgency,
                  description: t.prospectDetail.factors.timingUrgencyDesc,
                },
                {
                  key: "contact_availability",
                  label: "Contact availability",
                  value: lead_score!.contact_availability ?? 0,
                  description: "Phone/email/social/website/address reachability",
                },
                {
                  key: "personalization_quality",
                  label: "Personalization quality",
                  value: lead_score!.personalization_quality ?? 0,
                  description: "Pain specificity + industry match (outreach hook quality)",
                },
                {
                  key: "risk_penalty",
                  label: "Risk penalty",
                  value: -(lead_score!.risk_penalty ?? 0),
                  description: "Source reputation + data quality deductions",
                  inverted: true,
                },
              ]}
              total={lead_score!.total_score}
              grade={lead_score!.grade}
            />
            {lead_score!.reasoning && (
              <div className="mt-4 p-3 rounded-lg bg-muted/30 text-xs text-muted-foreground leading-relaxed">
                <p className="font-medium text-foreground mb-1">{t.prospectDetail.reasoning}</p>
                {lead_score!.reasoning}
              </div>
            )}
          </CardContent>
        </Card>
      ) : (
        <Card>
          <CardContent className="p-6">
            <EmptyState
              icon={<Sparkles className="h-5 w-5" />}
              title={t.prospectDetail.notYetAnalyzed}
              description={t.prospectDetail.notYetAnalyzedDesc}
              action={
                <Button onClick={handleReanalyze} disabled={analyzing}>
                  {analyzing ? (
                    <RefreshCw className="h-4 w-4 animate-spin" />
                  ) : (
                    <Sparkles className="h-4 w-4" />
                  )}
                  Run analyst
                </Button>
              }
            />
          </CardContent>
        </Card>
      )}

      {/* Tech stack + Pain points side-by-side */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Tech stack */}
        <Card>
          <CardHeader>
            <CardTitle className="text-lg flex items-center gap-2">
              <Server className="h-4 w-4 text-muted-foreground" />
              Tech stack
            </CardTitle>
            <CardDescription>
              Fingerprinted from website headers + HTML
            </CardDescription>
          </CardHeader>
          <CardContent>
            {tech_stack ? (
              <div className="space-y-3">
                <div className="grid grid-cols-2 gap-3 text-sm">
                  <TechField
                    label={t.prospectDetail.tech.cms}
                    value={tech_stack.cms}
                    fallback="—"
                  />
                  <TechField
                    label={t.prospectDetail.tech.framework}
                    value={tech_stack.framework}
                    fallback="—"
                  />
                  <TechField
                    label={t.prospectDetail.tech.hosting}
                    value={tech_stack.hosting_provider}
                    fallback="—"
                  />
                  <TechField
                    label="SSL"
                    value={
                      tech_stack.has_ssl === true
                        ? "✓ Active"
                        : tech_stack.has_ssl === false
                          ? "✗ Inactive"
                          : null
                    }
                    fallback="—"
                  />
                </div>
                {tech_stack.technologies.length > 0 && (
                  <div>
                    <p className="text-xs uppercase tracking-wider text-muted-foreground font-semibold mb-2">
                      Detected technologies
                    </p>
                    <div className="flex flex-wrap gap-1.5">
                      {tech_stack.technologies.map((t: string) => (
                        <span
                          key={t}
                          className="text-xs font-mono px-2 py-0.5 rounded bg-muted text-muted-foreground"
                        >
                          {t}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
                {tech_stack.issues.length > 0 && (
                  <div>
                    <p className="text-xs uppercase tracking-wider text-muted-foreground font-semibold mb-2 flex items-center gap-1.5">
                      <AlertTriangle className="h-3 w-3 text-amber-500" />
                      Issues
                    </p>
                    <ul className="space-y-1.5">
                      {tech_stack.issues.map((issue: string) => (
                        <li
                          key={issue}
                          className="text-xs text-muted-foreground flex items-start gap-1.5"
                        >
                          <span className="text-rose-500 mt-0.5">•</span>
                          <span className="font-mono">{issue}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            ) : (
              <EmptyState
                icon={<Zap className="h-5 w-5" />}
                title={t.prospectDetail.tech.noAudit}
                description={t.prospectDetail.tech.noAuditDesc}
                action={
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={handleReanalyze}
                    disabled={analyzing}
                  >
                    Run audit
                  </Button>
                }
              />
            )}
          </CardContent>
        </Card>

        {/* Pain points */}
        <Card>
          <CardHeader>
            <CardTitle className="text-lg flex items-center gap-2">
              <AlertTriangle className="h-4 w-4 text-muted-foreground" />
              Pain points
              {pain_points.length > 0 && (
                <span className="ml-auto text-xs font-normal text-muted-foreground">
                  {pain_points.length} detected
                </span>
              )}
            </CardTitle>
            <CardDescription>
              Issues that suggest buying intent
            </CardDescription>
          </CardHeader>
          <CardContent>
            {pain_points.length === 0 ? (
              <EmptyState
                icon={<CheckCircle2 className="h-5 w-5 text-emerald-500" />}
                title={t.prospectDetail.noPainPoints}
                description={t.prospectDetail.noPainPointsDesc}
                action={
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={handleReanalyze}
                    disabled={analyzing}
                  >
                    Run detector
                  </Button>
                }
              />
            ) : (
              <ul className="space-y-2.5">
                {pain_points.map((p) => (
                  <li
                    key={p.id}
                    className={cn(
                      "p-3 rounded-lg border border-border bg-card",
                      getSeverityBg(String(p.severity)),
                    )}
                  >
                    <div className="flex items-start gap-2.5">
                      <span
                        className={cn(
                          "mt-0.5 inline-flex items-center justify-center h-5 min-w-5 px-1.5 rounded text-xs font-bold uppercase",
                          getSeverityBadge(String(p.severity)),
                        )}
                      >
                        {p.severity}
                      </span>
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium leading-snug">
                          {p.category}
                        </p>
                        <p className="text-xs text-muted-foreground leading-relaxed mt-0.5">
                          {p.description}
                        </p>
                      </div>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>

        {/* T9.0: Social signals (Twitter + Threads) */}
        <SignalList
          signals={signals || []}
          onReanalyze={handleReanalyze}
          reanalyzing={analyzing}
        />

        {/* Sprint 3A: sequence enrollments + controls */}
        <EnrollmentPanel prospectId={prospect.id} />
      </div>

      {/* AI-generated hooks */}
      <Card>
        <CardHeader>
          <div className="flex items-start justify-between gap-4">
            <div>
              <CardTitle className="text-lg flex items-center gap-2">
                <MessageSquare className="h-4 w-4 text-muted-foreground" />
                Outreach hooks
                {hooks.length > 0 && (
                  <span className="ml-2 text-xs font-normal text-muted-foreground">
                    {hooks.length} AI-generated angles
                  </span>
                )}
              </CardTitle>
              <CardDescription>
                Personalized opening lines based on the prospect's pain points
                + tech stack. Use these in emails or WhatsApp messages.
              </CardDescription>
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={handleGenerateHooks}
              disabled={generatingHooks}
            >
              {generatingHooks ? (
                <RefreshCw className="h-4 w-4 animate-spin" />
              ) : (
                <Sparkles className="h-4 w-4" />
              )}
              {hooks.length === 0 ? t.prospectDetail.generateHooks : t.prospectDetail.regenerate}
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {hooks.length === 0 ? (
            <EmptyState
              icon={<MessageSquare className="h-5 w-5" />}
              title={t.prospectDetail.noHooksYet}
              description={t.prospectDetail.noHooksYetDesc}
            />
          ) : (
            <ul className="space-y-3">
              {hooks.map((hook, i) => (
                <li
                  key={hook.id}
                  className="p-4 rounded-lg border border-border bg-card hover:border-violet-300 transition-colors"
                >
                  <div className="flex items-start gap-3">
                    <div className="flex-shrink-0 h-7 w-7 rounded-full bg-gradient-to-br from-violet-500 to-indigo-600 text-white flex items-center justify-center text-sm font-bold">
                      {i + 1}
                    </div>
                    <div className="flex-1 min-w-0 space-y-2">
                      {hook.audit_finding && (
                        <p className="text-xs text-muted-foreground leading-relaxed">
                          <span className="font-medium text-foreground">Finding: </span>
                          {stripBracketedPrefix(hook.audit_finding)}
                        </p>
                      )}
                      <p className="text-sm leading-relaxed">
                        {hook.hook_text}
                      </p>
                      <div className="flex items-center justify-between gap-2 pt-1 flex-wrap">
                        <div className="flex items-center gap-2 flex-wrap">
                          {hook.recommended_service && (
                            <span className="inline-flex items-center gap-1 text-xs font-medium text-violet-600 bg-violet-100 dark:bg-violet-900/30 px-2 py-0.5 rounded">
                              <Tag className="h-3 w-3" />
                              {hook.recommended_service}
                            </span>
                          )}
                          <span
                            className={cn(
                              "text-xs font-medium num tabular-nums",
                              getConfidenceColor(hook.confidence ?? 0),
                            )}
                            title={t.prospectDetail.confidenceScore}
                          >
                            {Math.round((hook.confidence ?? 0) * 100)}% confident
                          </span>
                        </div>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleCopyHook(hook.hook_text, hook.id)}
                          className="h-7"
                        >
                          {copiedHookId === hook.id ? (
                            <>
                              <Check className="h-3.5 w-3.5" />
                              Copied
                            </>
                          ) : (
                            <>
                              <Copy className="h-3.5 w-3.5" />
                              Copy
                            </>
                          )}
                        </Button>
                      </div>
                    </div>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

// --- Sub-components ---

function TechField({
  label,
  value,
  fallback,
}: {
  label: string;
  value: string | null | undefined;
  fallback: string;
}) {
  return (
    <div>
      <p className="text-xs uppercase tracking-wider text-muted-foreground font-semibold mb-0.5">
        {label}
      </p>
      <p className="text-sm font-medium capitalize">
        {value || fallback}
      </p>
    </div>
  );
}

function DetailSkeleton() {
  return (
    <div className="space-y-6">
      <Skeleton className="h-8 w-32" />
      <Skeleton className="h-40" />
      <div className="grid grid-cols-1 md:grid-cols-[200px_1fr] gap-6">
        <Skeleton className="h-48" />
        <div className="space-y-3">
          <Skeleton className="h-10" />
          <Skeleton className="h-10" />
          <Skeleton className="h-10" />
          <Skeleton className="h-10" />
          <Skeleton className="h-10" />
        </div>
      </div>
      <div className="grid grid-cols-2 gap-6">
        <Skeleton className="h-48" />
        <Skeleton className="h-48" />
      </div>
      <Skeleton className="h-64" />
    </div>
  );
}

// --- Helpers ---

function formatRelative(iso: string): string {
  const then = new Date(iso).getTime();
  if (Number.isNaN(then)) return "—";
  const diff = Date.now() - then;
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

function truncateUrl(url: string, max: number): string {
  if (url.length <= max) return url;
  return url.slice(0, max - 3) + "...";
}

function stripBracketedPrefix(text: string): string {
  // Backend prepends "[MEDIUM] Title\n" — strip the prefix
  return text.replace(/^\[[^\]]+\]\s*[^\n]*\n?/, "").trim();
}

function getSeverityBg(sev: string): string {
  switch (sev) {
    case "high":
      return "border-rose-200 dark:border-rose-900/50";
    case "medium":
      return "border-amber-200 dark:border-amber-900/50";
    case "low":
      return "border-sky-200 dark:border-sky-900/50";
    default:
      return "";
  }
}

function getSeverityBadge(sev: string): string {
  switch (sev) {
    case "high":
      return "bg-rose-100 text-rose-700 dark:bg-rose-900/30 dark:text-rose-400";
    case "medium":
      return "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400";
    case "low":
      return "bg-sky-100 text-sky-700 dark:bg-sky-900/30 dark:text-sky-400";
    default:
      return "bg-muted text-muted-foreground";
  }
}

function getConfidenceColor(c: number): string {
  if (c >= 0.7) return "text-emerald-600";
  if (c >= 0.5) return "text-sky-600";
  return "text-muted-foreground";
}
