import { useMutation, useQueryClient } from "@tanstack/react-query";
import { runOptimization, type RunOptimizationBody } from "../api/optimization";
import { queryKeys } from "../lib/queryKeys";

/** Wraps POST /api/v1/optimization/run as a mutation — `isPending` drives
 * the "Running optimization..." state and disables the Run button, so a
 * user can't double-submit while the LP solve is in flight (M7 Sec. 21).
 * A successful result is also cached under a query key keyed by
 * (scenario, service_level, lead_time_days), so switching back to a
 * previously-run set of parameters can read the cached result instead of
 * re-invoking the solver. */
export function useOptimizationRun() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: RunOptimizationBody) => runOptimization(body),
    onSuccess: (data, variables) => {
      queryClient.setQueryData(queryKeys.optimizationRun(variables), data);
    },
  });
}
