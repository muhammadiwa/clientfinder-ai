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

export async function listProspects(
  filters: ProspectFilters = {},
): Promise<ProspectListResponse> {
  const { data } = await api.get<ProspectListResponse>("/prospects", {
    params: filters,
  });
  return data;
}

export async function getProspect(id: string): Promise<Prospect> {
  const { data } = await api.get<Prospect>(`/prospects/${id}`);
  return data;
}

export async function createProspect(
  payload: Omit<Prospect, "id" | "created_at" | "updated_at" | "owner_id" | "discovered_at">,
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

export async function deleteProspect(id: string, hard = false): Promise<void> {
  await api.delete(`/prospects/${id}`, { params: { hard_delete: hard } });
}
