/**
 * AI Analyzer — orchestrator for the analyst pipeline (T5, A29).
 *
 * Frontend-level orchestrator that:
 *  1. Fetches prospect data + pains + tech from /api/v1/prospects/:id/detail
 *  2. Optionally calls the LLM to generate richer analysis or
 *     re-score the prospect
 *  3. Generates outreach hooks (via LLM or template fallback)
 *  4. Caches results in localStorage for offline/preview use
 *
 * The actual LLM API key is held by the backend — this layer
 * just orchestrates the calls and provides caching + fallback.
 */

import { complete, isLLMAvailable, safeParseJson, type LLMResult } from "./llm";
import {
  buildOutreachEmailPrompt,
  buildPainAnalysisPrompt,
  type PainLike,
  type TechLike,
} from "./prompt-builder";
import { api } from "@/api/client";
import type { Prospect } from "@/types";

// --- Types ---

export interface GeneratedHook {
  audit_finding: string;
  hook_text: string;
  recommended_service: string;
  confidence: number;
}

export interface OutreachEmail {
  subject: string;
  body: string;
}

export interface AnalysisSummary {
  prospect_id: string;
  source: "backend" | "llm" | "template" | "cache";
  llm_provider?: string;
  llm_model?: string;
  hooks: GeneratedHook[];
  grade?: string;
  total_score?: number;
  llm_available: boolean;
  generated_at: number;
}

export interface ProspectDetail {
  prospect: Prospect;
  tech_stack: TechLike | null;
  pain_points: PainLike[];
  lead_score: {
    signal_strength: number;
    pain_severity: number;
    budget_indicator: number;
    solution_fit: number;
    timing_urgency: number;
    total_score: number;
    grade: string;
    reasoning: string | null;
    scored_at: string;
  } | null;
  hooks: {
    id: string;
    hook_text: string;
    audit_finding: string | null;
    recommended_service: string | null;
    confidence: number;
    is_used: string;
  }[];
}

// --- Caching (localStorage) ---

const CACHE_TTL_MS = 1000 * 60 * 60 * 24; // 24h
const CACHE_KEY_PREFIX = "cf-analysis:";

interface CacheEntry {
  data: AnalysisSummary;
  expiresAt: number;
}

function getCacheKey(prospectId: string): string {
  return `${CACHE_KEY_PREFIX}${prospectId}`;
}

export function clearAnalysisCache(prospectId?: string): void {
  if (typeof window === "undefined") return;
  if (prospectId) {
    window.localStorage.removeItem(getCacheKey(prospectId));
  } else {
    Object.keys(window.localStorage)
      .filter((k) => k.startsWith(CACHE_KEY_PREFIX))
      .forEach((k) => window.localStorage.removeItem(k));
  }
}

function readCache(prospectId: string): AnalysisSummary | null {
  if (typeof window === "undefined") return null;
  const raw = window.localStorage.getItem(getCacheKey(prospectId));
  if (!raw) return null;
  try {
    const entry = JSON.parse(raw) as CacheEntry;
    if (entry.expiresAt < Date.now()) {
      window.localStorage.removeItem(getCacheKey(prospectId));
      return null;
    }
    return { ...entry.data, source: "cache" };
  } catch {
    return null;
  }
}

function writeCache(summary: AnalysisSummary): void {
  if (typeof window === "undefined") return;
  const entry: CacheEntry = {
    data: summary,
    expiresAt: Date.now() + CACHE_TTL_MS,
  };
  try {
    window.localStorage.setItem(
      getCacheKey(summary.prospect_id),
      JSON.stringify(entry),
    );
  } catch {
    // Quota exceeded; ignore
  }
}

// --- API: fetch prospect detail ---

export async function fetchProspectDetail(
  prospectId: string,
): Promise<ProspectDetail> {
  const { data } = await api.get<ProspectDetail>(
    `/prospects/${prospectId}/detail`,
  );
  return data;
}

// --- API: enrich (POST to backend) ---

export async function enrichProspect(
  prospectId: string,
): Promise<{
  ok: boolean;
  grade?: string;
  total_score?: number;
  n_pains?: number;
  error?: string;
}> {
  const { data } = await api.post(`/prospects/${prospectId}/enrich`);
  return data;
}

// --- API: generate hooks (calls backend endpoint) ---

export async function generateHooks(
  prospectId: string,
): Promise<{
  ok: boolean;
  source: "llm" | "template";
  provider?: string;
  hooks: GeneratedHook[];
  error?: string;
}> {
  const { data } = await api.post<{
    ok: boolean;
    source: "llm" | "template";
    provider?: string;
    hooks: GeneratedHook[];
    error?: string;
  }>(`/ai/hooks/${prospectId}`);
  return data;
}

// --- High-level orchestrator: analyze (with caching) ---

/**
 * Full analysis: fetch detail + generate hooks (if missing) +
 * cache result. Returns AnalysisSummary ready for UI.
 */
export async function analyzeProspect(
  prospectId: string,
  options: { force?: boolean; useCache?: boolean } = {},
): Promise<AnalysisSummary> {
  const { force = false, useCache = true } = options;

  // 1. Check cache
  if (useCache && !force) {
    const cached = readCache(prospectId);
    if (cached) return cached;
  }

  // 2. Fetch detail
  const detail = await fetchProspectDetail(prospectId);

  // 3. If hooks already exist, use them; otherwise generate
  let hooks: GeneratedHook[] = detail.hooks.map((h) => ({
    audit_finding: h.audit_finding ?? "",
    hook_text: h.hook_text,
    recommended_service: h.recommended_service ?? "",
    confidence: h.confidence,
  }));
  let source: AnalysisSummary["source"] = "backend";
  let provider: string | undefined;

  if (hooks.length === 0 || force) {
    try {
      const result = await generateHooks(prospectId);
      hooks = result.hooks;
      source = result.source;
      provider = result.provider;
    } catch (e) {
      console.warn("Hook generation failed:", e);
    }
  }

  // 4. Build summary
  const llmAvailable = await isLLMAvailable().catch(() => false);
  const summary: AnalysisSummary = {
    prospect_id: prospectId,
    source,
    llm_provider: provider,
    grade: detail.lead_score?.grade,
    total_score: detail.lead_score?.total_score,
    hooks,
    llm_available: llmAvailable,
    generated_at: Date.now(),
  };

  // 5. Cache
  writeCache(summary);
  return summary;
}

// --- Outreach email generation (T6 prep) ---

/**
 * Generate a full outreach email from a selected hook.
 */
export async function generateOutreachEmail(
  prospect: Prospect,
  hook: GeneratedHook,
  pains: PainLike[],
): Promise<OutreachEmail | null> {
  const { system, user } = buildOutreachEmailPrompt(
    prospect,
    hook.hook_text,
    pains,
  );
  const result: LLMResult = await complete({
    system,
    user,
    temperature: 0.5,
    maxTokens: 800,
    jsonMode: true,
  });
  if (result.error || !result.content) return null;
  return safeParseJson<OutreachEmail>(result.content);
}

// --- Pain analysis (richer, LLM-driven) ---

/**
 * Use LLM to identify additional pain points not caught by
 * the heuristic detector.
 */
export async function analyzePainsLLM(
  prospect: Prospect,
  existingPains: PainLike[],
): Promise<
  {
    kind: string;
    title: string;
    description: string;
    severity: number;
    recommended_service: string;
  }[]
> {
  const { system, user } = buildPainAnalysisPrompt(prospect, existingPains);
  const result = await complete({
    system,
    user,
    temperature: 0.3,
    maxTokens: 1200,
    jsonMode: true,
  });
  if (result.error || !result.content) return [];
  const parsed = safeParseJson<{
    additional_pains: {
      kind: string;
      title: string;
      description: string;
      severity: number;
      recommended_service: string;
    }[];
  }>(result.content);
  if (!parsed?.additional_pains) return [];
  return parsed.additional_pains;
}

// --- Re-exports ---

export {
  complete,
  safeParseJson,
  isLLMAvailable,
  type LLMResult,
} from "./llm";
export {
  buildPainAnalysisPrompt,
  buildOutreachEmailPrompt,
  type PainLike,
  type TechLike,
} from "./prompt-builder";
