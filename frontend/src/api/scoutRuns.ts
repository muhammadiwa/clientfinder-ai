/**
 * ScoutRun API client (Sprint 4 PR 3).
 *
 * Powers the /scout-runs/:id/results page (the Layer 2 of the
 * hybrid C display from the redesign). The endpoint returns
 * the ScoutRun metadata + a paginated page of prospects
 * filtered by scout_run_id.
 */

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
  token: string,
): Promise<ScoutRunResultsResponse> {
  const params = new URLSearchParams({
    page: String(page),
    per_page: String(perPage),
  });
  const res = await fetch(
    `${API_BASE}/scraping/scout-runs/${runId}/results?${params}`,
    { headers: { Authorization: `Bearer ${token}` } },
  );
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(
      err.detail || `Failed to load ScoutRun results (${res.status})`,
    );
  }
  return res.json();
}
