import { useQuery } from "@tanstack/react-query";
import { getOptimizationScenarios } from "../api/optimization";
import { STALE_TIME } from "../lib/queryConfig";
import { queryKeys } from "../lib/queryKeys";

export function useOptimizationScenarios() {
  return useQuery({
    queryKey: queryKeys.optimizationScenarios,
    queryFn: ({ signal }) => getOptimizationScenarios(signal),
    staleTime: STALE_TIME.LONG,
  });
}
