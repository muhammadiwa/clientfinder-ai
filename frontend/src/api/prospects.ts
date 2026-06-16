import { api } from "./client";
import type { Prospect, ProspectListResponse } from "@/types";

// Inline types for the ProspectDetailResponse shape.
// These mirror the backend's Pydantic schemas (see
// backend/app/models/prospect.py + lead.py) but are kept local
// to the frontend to avoid coupling the UI to backend model
// internals.
export interface TechStack {
  id: string;
  cms: string | null;
  framework: string | null;
  has_ssl: boolean | null;
  has_viewport_meta: boolean;
  payment_gateways: string[];
  body_bytes_read: number | null;
  technologies: string[];
  hosting_provider: string | null;
  issues: string[];
  audited_at: string;
}

export interface PainPoint {
  id: string;
  category: string;
  severity: number;
  description: string | null;
  source: string | null;
}

export interface LeadScore {
  id: string;
  grade: string;
  total: number;
  total_score: number;     // alias for some callers
  reasoning: string | null;
  // 9-factor score breakdown (mirrors backend/app/services/analyzer/scorer.py:ScoreBreakdown)
  signal_strength: number;
  pain_severity: number;
  budget_indicator: number;
  solution_fit: number;
  timing_urgency: number;
  contact_availability: number;
  personalization_quality: number;
  tier: number;
  industry_specificity: number;
  risk_penalty: number;
  scored_at: string;
}

export interface Hook {
  id: string;
  hook_text: string;
  audit_finding: string | null;
  recommended_service: string | null;
  confidence: number | null;   // 0.0-1.0 (from T5 LLM analyst)
  is_used: boolean;
}

export interface ProspectFilters {
  page?: number;
  per_page?: number;
  status?: string;
  source?: string;
  industry?: string;
  grade?: string;
  min_score?: number;
  search?: string;
  include_deleted?: boolean;
}

export interface ProspectDetailResponse {
  prospect: Prospect;
  tech_stack: TechStack | null;
  pain_points: PainPoint[];
  lead_score: LeadScore | null;
  hooks: Hook[];
  signals: SignalItem[];
  // Sprint 4 PR 3: link to the ScoutRun that found this
  // prospect. Powers the breadcrumb on ProspectDetail.
  // Nullable for legacy + manually-imported prospects.
  scout_run_id?: string | null;
  // C2 review: the count hint was removed from the breadcrumb
  // because the /prospects/{id} endpoint doesn't return a
  // run-level total. The count is visible on the
  // /scout-runs/:id/results page (Layer 2) instead.
}

export interface SignalItem {
  id: string;
  signal_type: string;
  source: string;
  source_url: string | null;
  raw_text: string | null;
  weight: number;
  detected_at: string | null;
}

export async function listProspects(
  filters: ProspectFilters = {},
): Promise<ProspectListResponse> {
  const params: Record<string, string | number | boolean> = {};
  if (filters.page != null) params.page = filters.page;
  if (filters.per_page != null) params.per_page = filters.per_page;
  if (filters.status) params.status = filters.status;
  if (filters.source) params.source = filters.source;
  if (filters.industry) params.industry = filters.industry;
  if (filters.grade) params.grade = filters.grade;
  if (filters.min_score != null) params.min_score = filters.min_score;
  if (filters.search) params.search = filters.search;
  if (filters.include_deleted) params.include_deleted = true;
  const { data } = await api.get<ProspectListResponse>("/prospects", {
    params,
  });
  return data;
}

export async function getProspect(id: string): Promise<Prospect> {
  const { data } = await api.get<Prospect>(`/prospects/${id}`);
  return data;
}

// --- Lead classification (Sprint 3B) ---

export type Tier = "smb" | "mid" | "enterprise" | "unknown";

export interface ClassifyResult {
  tier: Tier;
  tier_confidence: number;
  tier_reasoning: string;
  industry_specific: string;
  industry_category: string;
  industry_confidence: number;
  industry_rationale: string;
}

export async function classifyProspect(
  id: string,
): Promise<ClassifyResult> {
  const { data } = await api.post<ClassifyResult>(
    `/prospects/${id}/classify`,
  );
  return data;
}

export async function getProspectDetail(
  id: string,
): Promise<ProspectDetailResponse> {
  const { data } = await api.get<ProspectDetailResponse>(
    `/prospects/${id}/detail`,
  );
  return data;
}

export async function enrichProspect(
  id: string,
): Promise<{
  ok: boolean;
  grade?: string;
  total_score?: number;
  n_pains?: number;
  error?: string;
}> {
  const { data } = await api.post(`/prospects/${id}/enrich`);
  return data;
}

/**
 * T8.6: re-fetch the prospect's homepage and extract phone, email,
 * address, and social links. Overwrites existing fields (homepage
 * is canonical per the spec). Triggers a Playwright fetch in the
 * backend — typically 3-10s per call.
 */
export interface RefreshContactResponse {
  ok: boolean;
  status: "ok" | "no_data" | "timeout" | "error";
  ms: number;
  fields: {
    phone: string | null;
    email: string | null;
    address: string | null;
    socials: Record<string, string>;
  };
}

export async function refreshContact(
  id: string,
): Promise<RefreshContactResponse> {
  const { data } = await api.post<RefreshContactResponse>(
    `/prospects/${id}/refresh-contact`,
  );
  return data;
}

export async function createProspect(
  payload: Partial<Prospect>,
): Promise<Prospect> {
  const { data } = await api.post<Prospect>("/prospects", payload);
  return data;
}

export async function updateProspect(
  id: string,
  payload: Partial<Prospect>,
): Promise<Prospect> {
  const { data } = await api.patch<Prospect>(`/prospects/${id}`, payload);
  return data;
}

export async function deleteProspect(
  id: string,
  hard = false,
): Promise<void> {
  await api.delete(`/prospects/${id}`, { params: { hard_delete: hard } });
}
