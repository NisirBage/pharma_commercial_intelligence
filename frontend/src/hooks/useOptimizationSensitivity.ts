import { useQuery } from "@tanstack/react-query";
import { getOptimizationSensitivity, type GetSensitivityParams } from "../api/optimization";
import { STALE_TIME } from "../lib/queryConfig";
import { queryKeys } from "../lib/queryKeys";

/** Pass `null` to disable the query (e.g. before the user has picked an
 * ATC class to inspect sensitivity for). */
export function useOptimizationSensitivity(params: GetSensitivityParams | null) {
  return useQuery({
    queryKey: params ? queryKeys.optimizationSensitivity(params) : (["optimizationSensitivity", "disabled"] as const),
    queryFn: ({ signal }) => getOptimizationSensitivity(params as GetSensitivityParams, signal),
    staleTime: STALE_TIME.MEDIUM,
    enabled: params !== null,
  });
}
