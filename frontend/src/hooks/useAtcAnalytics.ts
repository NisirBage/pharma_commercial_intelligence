import { useQuery } from "@tanstack/react-query";
import { getAtcAnalytics } from "../api/analytics";
import { STALE_TIME } from "../lib/queryConfig";
import { queryKeys } from "../lib/queryKeys";

export function useAtcAnalytics() {
  return useQuery({
    queryKey: queryKeys.atcAnalytics,
    queryFn: ({ signal }) => getAtcAnalytics(signal),
    staleTime: STALE_TIME.LONG,
  });
}
