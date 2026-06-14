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
  prospect: ProspectItem;
  tech_stack: TechStackData | null;
  pain_points: PainPointItem[];
  lead_score: LeadScoreData | null;
  hooks: HookItem[];
  signals: SignalItem[];
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
