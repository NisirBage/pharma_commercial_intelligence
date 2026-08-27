import { useQuery } from "@tanstack/react-query";
import { getKpiSummary } from "../api/kpis";
import { STALE_TIME } from "../lib/queryConfig";
import { queryKeys } from "../lib/queryKeys";

export function useKpiSummary() {
  return useQuery({
    queryKey: queryKeys.kpiSummary,
    queryFn: ({ signal }) => getKpiSummary(signal),
    staleTime: STALE_TIME.LONG,
  });
}
