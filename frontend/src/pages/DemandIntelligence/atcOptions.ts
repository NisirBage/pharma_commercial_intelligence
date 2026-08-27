import { ATC_CLASSES } from "../../types/api";

/** Shared "Aggregate + one of the 8 observed ATC classes" selector
 * options for Trends/Seasonality/Anomalies — all three call their
 * endpoint with `atc_class` omitted for the aggregate (see
 * backend/app/services/sales_service.py, seasonality_service.py,
 * anomaly_service.py), so the "Aggregate" option's value is `""`, and
 * every call site converts it back to `undefined` before calling a hook. */
export const ATC_SELECT_OPTIONS = [
  { value: "", label: "Aggregate (all classes)" },
  ...ATC_CLASSES.map((atcClass) => ({ value: atcClass, label: atcClass })),
];

/** `""` (the Select's "Aggregate" sentinel) -> `undefined` (what every
 * hook/API module expects for "omit this filter"). */
export function toAtcClassParam(selectValue: string): string | undefined {
  return selectValue === "" ? undefined : selectValue;
}
