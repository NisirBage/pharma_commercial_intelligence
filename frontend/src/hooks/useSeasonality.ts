import { useQuery } from "@tanstack/react-query";
import { getSeasonality } from "../api/analytics";
import { STALE_TIME } from "../lib/queryConfig";
import { queryKeys } from "../lib/queryKeys";

export function useSeasonality(atcClass?: string) {
  return useQuery({
    queryKey: queryKeys.seasonality(atcClass),
    queryFn: ({ signal }) => getSeasonality(atcClass, signal),
    staleTime: STALE_TIME.LONG,
  });
}
