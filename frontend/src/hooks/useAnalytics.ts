/**
 * useAnalytics — TanStack Query hooks for analytics data.
 *
 * T8.5+++++++ (Dashboard stats wiring): these hooks
 * centralize the analytics endpoint calls so the
 * Dashboard can replace its synthetic data with real
 * server-side aggregates.
 *
 * The queryKey encodes the `days` parameter so different
 * time windows don't collide in cache.
 */
import { useQuery, type UseQueryResult } from "@tanstack/react-query";

import * as analyticsApi from "@/api/analytics";
import type { AnalyticsOverview } from "@/api/analytics";

/**
 * useAnalyticsOverview — fetches the full analytics
 * overview (all 4 KPI categories) for the given lookback
 * period.
 *
 * Powers the Dashboard's "Pipeline activity" chart
 * (replaces the previous synthetic sin-based data) +
 * other future real-data Dashboard widgets.
 */
export function useAnalyticsOverview(
  days = 30,
): UseQueryResult<AnalyticsOverview, Error> {
  return useQuery({
    queryKey: ["analytics", "overview", days] as const,
    queryFn: () => analyticsApi.getAnalyticsOverview(days),
    staleTime: 60_000, // 1min — analytics is "fresh" for 1min
    refetchOnWindowFocus: true,
  });
}
