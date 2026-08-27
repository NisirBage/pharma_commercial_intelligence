import { useQuery } from "@tanstack/react-query";
import { getForecastDiagnostics } from "../api/forecasting";
import { STALE_TIME } from "../lib/queryConfig";
import { queryKeys } from "../lib/queryKeys";

export function useForecastDiagnostics(atcClass: string) {
  return useQuery({
    queryKey: queryKeys.forecastDiagnostics(atcClass),
    queryFn: ({ signal }) => getForecastDiagnostics(atcClass, signal),
    staleTime: STALE_TIME.FORECAST,
    enabled: Boolean(atcClass),
  });
}
