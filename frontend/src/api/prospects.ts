import { api } from "./client";
import type { Prospect, ProspectListResponse } from "@/types";

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
  tech_stack: {
    cms: string | null;
    framework: string | null;
    hosting_provider: string | null;
    has_ssl: boolean | null;
    page_speed_score: number | null;
    technologies: string[];
    issues: string[];
    audited_at: string | null;
  } | null;
  pain_points: {
    id: string;
    category: string;
    severity: string;
    description: string;
    evidence_quote: string | null;
    source: string | null;
    detected_at: string;
  }[];
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
