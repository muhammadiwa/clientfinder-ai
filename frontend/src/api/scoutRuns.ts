/**
 * ScoutRun API client (Sprint 4 PR 3, refactored Sprint 4.1).
 *
 * Powers the /scout-runs/:id/results page (the Layer 2 of the
 * hybrid C display from the redesign). The endpoint returns
 * the ScoutRun metadata + a paginated page of prospects
 * filtered by scout_run_id.
 *
 * Sprint 4.1 followup: now uses the shared `api` axios
 * instance (with auth interceptor + refresh-on-401) instead
 * of raw fetch + manual token param. This was the C2 finding
 * from the holistic Sprint 4 review — three different auth
 * patterns (fetch+token, axios+interceptor, localStorage
 * direct) for the same JWT, in the same sprint.
 */

import { api } from "./client";

const API_BASE = import.meta.env.VITE_API_URL || "/api/v1";

export interface ScoutRunMeta {
  id: string;
  source: string;
  query: Record<string, unknown> | null;
  status: string;
  prospects_found: number;
  started_at: string | null;
  completed_at: string | null;
  created_at: string | null;
  error_message: string | null;
}

export interface ScoutRunProspect {
  id: string;
  company_name: string;
  website: string | null;
  phone: string | null;
  source: string;
  source_url: string | null;
  raw_data: Record<string, unknown>;
  status: string;
  scout_run_id: string | null;
  created_at: string;
}

export interface ScoutRunResultsResponse {
  run: ScoutRunMeta;
  results: ScoutRunProspect[];
  total: number;
  page: number;
  per_page: number;
  pages: number;
}

export async function getScoutRunResults(
  runId: string,
  page: number = 1,
  perPage: number = 25,
): Promise<ScoutRunResultsResponse> {
  const { data } = await api.get<ScoutRunResultsResponse>(
    `${API_BASE}/scraping/scout-runs/${runId}/results`,
    { params: { page, per_page: perPage } },
  );
  return data;
}
