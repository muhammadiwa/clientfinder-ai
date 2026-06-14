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

export type { AnalyticsOverview, AnalyticsRange };
