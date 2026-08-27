import { useQuery } from "@tanstack/react-query";
import { getAnomalies, type GetAnomaliesParams } from "../api/anomalies";
import { STALE_TIME } from "../lib/queryConfig";
import { queryKeys } from "../lib/queryKeys";

export function useAnomalies(params: GetAnomaliesParams) {
  return useQuery({
    queryKey: queryKeys.anomalies(params),
    queryFn: ({ signal }) => getAnomalies(params, signal),
    staleTime: STALE_TIME.MEDIUM,
  });
}
