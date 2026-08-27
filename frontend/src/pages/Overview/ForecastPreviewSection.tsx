import type { UseQueryResult } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { Card } from "../../components/ui/Card/Card";
import { EmptyState } from "../../components/ui/EmptyState/EmptyState";
import { ErrorState } from "../../components/ui/ErrorState/ErrorState";
import { MetricCard } from "../../components/ui/MetricCard/MetricCard";
import { SectionHeader } from "../../components/ui/SectionHeader/SectionHeader";
import { Skeleton } from "../../components/ui/Skeleton/Skeleton";
import { formatDecimal, formatPercent } from "../../lib/format";
import type { ForecastResponse } from "../../types/api";
import styles from "./Overview.module.css";

export interface ForecastPreviewSectionProps {
  query: UseQueryResult<ForecastResponse, unknown>;
}

/** "What is expected next?" — the same aggregate forecast
 * (GET /api/v1/forecast/aggregate, `useForecast(undefined)`) the
 * Forecasting page itself reads first, via the identical query key, so
 * navigating to /forecast right after Overview is typically a cache
 * hit rather than a second request. Every value here is a direct field
 * from the response — the next horizon point's own prediction/interval,
 * the model name, and the backend's own backtested WAPE — no client-side
 * averaging or re-derivation of the 14-day series (that analysis stays
 * on the Forecasting page). Per-class growing/declining signals are
 * already surfaced by Commercial Signals above; this section doesn't
 * repeat them. */
export function ForecastPreviewSection({ query }: ForecastPreviewSectionProps) {
  const { data, isLoading, isError, error, refetch } = query;
  const firstPoint = data?.forecast[0];

  return (
    <section aria-labelledby="forecast-preview-heading">
      <SectionHeader
        id="forecast-preview-heading"
        eyebrow="Forecast"
        title="Forecasting Intelligence"
        description="The aggregate demand outlook for the next horizon."
        action={
          <Link to="/forecast" className={styles.sectionLink}>
            View forecasts →
          </Link>
        }
      />
      {isLoading ? (
        <Card>
          <Skeleton variant="text" count={3} />
        </Card>
      ) : isError ? (
        <ErrorState title="Couldn't load the forecast" error={error} onRetry={() => refetch()} />
      ) : !data || data.forecast.length === 0 ? (
        <EmptyState title="No forecast available" description="The API returned no forecast points for the aggregate series." />
      ) : (
        <div className={styles.previewGrid}>
          <MetricCard
            label="Next-Day Forecast"
            value={formatDecimal(firstPoint?.prediction)}
            unit={firstPoint?.prediction != null ? "units" : undefined}
            helperText={
              firstPoint?.lower != null && firstPoint.upper != null
                ? `Interval ${formatDecimal(firstPoint.lower)}–${formatDecimal(firstPoint.upper)}`
                : undefined
            }
            tooltip="The first day's predicted value from the aggregate forecast, with its prediction interval if the model provides one."
          />
          <MetricCard
            label="Forecast Accuracy (WAPE)"
            value={formatPercent(data.metrics.wape)}
            helperText="Weighted absolute percentage error, from backtesting"
            tooltip="Lower is better. The model's own backtested error rate, not computed here."
          />
          <MetricCard
            label="Model"
            value={data.model}
            helperText={`${data.horizon_days}-day aggregate horizon`}
            tooltip="The forecasting model M4 selected for the aggregate series."
          />
        </div>
      )}
    </section>
  );
}
