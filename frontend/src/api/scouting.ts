import { api } from "./client";
import type { ScrapingJob, ScrapingJobListResponse, ScrapingSource } from "@/types";

export interface ScrapingJobCreate {
  source: ScrapingSource;
  keywords: string;
  location?: string;
  max_results?: number;
}

export interface ScrapingPreset {
  id: string;
  name: string;
  source: ScrapingSource;
  query: {
    keywords: string;
    location: string | null;
    max_results: number;
  };
}

export async function createScrapingJob(
  payload: ScrapingJobCreate,
): Promise<ScrapingJob> {
  const { data } = await api.post<ScrapingJob>("/scraping/jobs", payload);
  return data;
}

export async function listScrapingJobs(
  page = 1,
  perPage = 20,
): Promise<ScrapingJobListResponse> {
  const { data } = await api.get<ScrapingJobListResponse>("/scraping/jobs", {
    params: { page, per_page: perPage },
  });
  return data;
}

export async function getScrapingJob(id: string): Promise<ScrapingJob> {
  const { data } = await api.get<ScrapingJob>(`/scraping/jobs/${id}`);
  return data;
}

export async function retryScrapingJob(id: string): Promise<ScrapingJob> {
  const { data } = await api.post<ScrapingJob>(`/scraping/jobs/${id}/retry`);
  return data;
}

export async function deleteScrapingJob(id: string): Promise<void> {
  await api.delete(`/scraping/jobs/${id}`);
}

export async function listScrapingPresets(): Promise<ScrapingPreset[]> {
  const { data } = await api.get<ScrapingPreset[]>("/scraping/presets");
  return data;
}
