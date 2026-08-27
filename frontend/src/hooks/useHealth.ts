import { useQuery } from "@tanstack/react-query";
import { getHealth } from "../api/health";
import { queryKeys } from "../lib/queryKeys";

/** Powers the Topbar's API status indicator. Refetches periodically (a
 * liveness signal should stay reasonably current) and never retries —
 * a failed health check should show as down promptly, not after 3
 * silent retries. */
export function useHealth() {
  return useQuery({
    queryKey: queryKeys.health,
    queryFn: ({ signal }) => getHealth(signal),
    staleTime: 60 * 1000,
    refetchInterval: 60 * 1000,
    retry: false,
  });
}
