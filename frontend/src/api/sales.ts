import { get } from "./client";
import { SalesTrendsSchema, type Grain, type SalesTrends } from "../types/api";

export interface GetSalesTrendsParams {
  atcClass?: string;
  startDate?: string;
  endDate?: string;
  grain?: Grain;
}

export function getSalesTrends(params: GetSalesTrendsParams = {}, signal?: AbortSignal): Promise<SalesTrends> {
  return get(
    "/api/v1/sales/trends",
    SalesTrendsSchema,
    {
      atc_class: params.atcClass,
      start_date: params.startDate,
      end_date: params.endDate,
      grain: params.grain,
    },
    signal,
  );
}
