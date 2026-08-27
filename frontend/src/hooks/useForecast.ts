import { useQuery } from "@tanstack/react-query";
import { getAggregateForecast, getForecast } from "../api/forecasting";
import { STALE_TIME } from "../lib/queryConfig";
import { queryKeys } from "../lib/queryKeys";

/** `atcClass` undefined -> GET /api/v1/forecast/aggregate (the direct
 * aggregate model, never a client-side sum of per-class forecasts). */
export function useForecast(atcClass: string | undefined) {
  return useQuery({
    queryKey: atcClass ? queryKeys.forecast(atcClass) : queryKeys.aggregateForecast,
    queryFn: ({ signal }) => (atcClass ? getForecast(atcClass, signal) : getAggregateForecast(signal)),
    staleTime: STALE_TIME.FORECAST,
  });
}
