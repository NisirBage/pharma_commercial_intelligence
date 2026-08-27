import { useQuery } from "@tanstack/react-query";
import { getDataQuality } from "../api/dataQuality";
import { STALE_TIME } from "../lib/queryConfig";
import { queryKeys } from "../lib/queryKeys";

export function useDataQuality() {
  return useQuery({
    queryKey: queryKeys.dataQuality,
    queryFn: ({ signal }) => getDataQuality(signal),
    staleTime: STALE_TIME.LONG,
  });
}
