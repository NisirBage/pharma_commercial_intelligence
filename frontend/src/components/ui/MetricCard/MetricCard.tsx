import { ArrowDown, ArrowUp, HelpCircle, Minus } from "lucide-react";
import { Card } from "../Card/Card";
import { Skeleton } from "../Skeleton/Skeleton";
import { StatusBadge, type Status } from "../StatusBadge/StatusBadge";
import { Tooltip } from "../Tooltip/Tooltip";
import styles from "./MetricCard.module.css";

export type TrendDirection = "up" | "down" | "flat";

export interface MetricCardProps {
  label: string;
  /** The metric value, already formatted by the caller (e.g. "2.4M",
   * "94.2%"). This component never formats or fabricates numbers —
   * callers supply real, API-sourced values. Optional only so a
   * `loading` card doesn't need a placeholder value; required in
   * practice whenever `loading` is false. */
  value?: string;
  unit?: string;
  trend?: string;
  trendDirection?: TrendDirection;
  helperText?: string;
  status?: Status;
  /** Explains the metric's definition/methodology, e.g. a KPI or
   * forecasting term. Rendered via the accessible Tooltip component. */
  tooltip?: string;
  /** While true, renders a Skeleton in place of the value/trend — for
   * a query that's still in flight. `value` is not required in this
   * state, so callers don't need a placeholder value while loading. */
  loading?: boolean;
}

const TREND_ICON: Record<TrendDirection, typeof ArrowUp> = {
  up: ArrowUp,
  down: ArrowDown,
  flat: Minus,
};

/** A single-metric summary card for KPI/overview surfaces. Infrastructure
 * only — this component renders whatever values it is given and must
 * never contain example/fabricated business data itself (M7.3 Sec. 24).
 * The M7.4 Overview page supplies real values from the API. */
export function MetricCard({ label, value, unit, trend, trendDirection, helperText, status, tooltip, loading = false }: MetricCardProps) {
  const TrendIcon = trendDirection ? TREND_ICON[trendDirection] : null;

  return (
    <Card>
      <div className={styles.header}>
        <span className={styles.label}>
          {label}
          {tooltip && (
            <Tooltip content={tooltip}>
              <button type="button" className={styles.tooltipTrigger} aria-label={`About ${label}`}>
                <HelpCircle size={13} aria-hidden="true" />
              </button>
            </Tooltip>
          )}
        </span>
        {!loading && status && <StatusBadge status={status} />}
      </div>
      {loading ? (
        <div className={styles.loadingBody}>
          <Skeleton variant="metric" />
        </div>
      ) : (
        <>
          <div className={styles.valueRow}>
            <span className={styles.value}>{value}</span>
            {unit && <span className={styles.unit}>{unit}</span>}
          </div>
          {trend && trendDirection && (
            <div className={`${styles.trend} ${styles[trendDirection]}`}>
              {TrendIcon && <TrendIcon size={14} aria-hidden="true" />}
              <span>{trend}</span>
            </div>
          )}
          {helperText && <p className={styles.helperText}>{helperText}</p>}
        </>
      )}
    </Card>
  );
}
