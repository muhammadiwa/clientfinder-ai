import { api } from "./client";
import type {
  AnalyticsOverview,
  AnalyticsRange,
} from "@/types";

export async function getAnalyticsOverview(
  days = 30,
): Promise<AnalyticsOverview> {
  const { data } = await api.get<AnalyticsOverview>(
    `/analytics/overview?days=${days}`,
  );
  return data;
}

// --- Sprint 3B carryover: tier distribution for the dashboard ---

export interface TierDistribution {
  smb: number;
  mid: number;
  enterprise: number;
  unknown: number;
  unclassified: number;
  total: number;
}

export async function getTierDistribution(
  days = 30,
): Promise<TierDistribution> {
  const { data } = await api.get<TierDistribution>(
    `/analytics/tier-distribution?days=${days}`,
  );
  return data;
}

export type { AnalyticsOverview, AnalyticsRange };
