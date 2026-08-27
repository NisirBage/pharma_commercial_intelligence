import { useQuery } from "@tanstack/react-query";
import { getSalesTrends, type GetSalesTrendsParams } from "../api/sales";
import { STALE_TIME } from "../lib/queryConfig";
import { queryKeys } from "../lib/queryKeys";

export function useSalesTrends(params: GetSalesTrendsParams) {
  return useQuery({
    queryKey: queryKeys.salesTrends(params),
    queryFn: ({ signal }) => getSalesTrends(params, signal),
    staleTime: STALE_TIME.MEDIUM,
  });
}
