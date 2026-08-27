import type { UseQueryResult } from "@tanstack/react-query";
import { MetricCard } from "../../components/ui/MetricCard/MetricCard";
import { ErrorState } from "../../components/ui/ErrorState/ErrorState";
import { formatCount, formatDate, formatDecimal, formatPercent } from "../../lib/format";
import type { KpiSummary } from "../../types/api";
import styles from "./Overview.module.css";

export interface KpiSummarySectionProps {
  query: UseQueryResult<KpiSummary, unknown>;
}

/** The 4-card KPI row — total/average/peak demand plus the dominant
 * ATC class, straight from GET /api/v1/kpis/summary. */
export function KpiSummarySection({ query }: KpiSummarySectionProps) {
  const { data, isLoading, isError, error, refetch } = query;

  if (isError) {
    return <ErrorState title="Couldn't load the KPI summary" error={error} onRetry={() => refetch()} />;
  }

  const dominantShare =
    data?.dominant_atc_share_pct != null ? `${formatPercent(data.dominant_atc_share_pct)} of total demand` : undefined;

  return (
    <div className={styles.kpiGrid}>
      <MetricCard
        label="Total Demand"
        value={formatCount(data?.total_demand)}
        unit={data?.total_demand != null ? "units" : undefined}
        loading={isLoading}
        tooltip="Sum of observed daily demand across all ATC classes over the full data period."
      />
      <MetricCard
        label="Avg Daily Demand"
        value={formatDecimal(data?.average_daily_demand)}
        unit={data?.average_daily_demand != null ? "units/day" : undefined}
        loading={isLoading}
        tooltip="Mean daily demand across the full data period."
      />
      <MetricCard
        label="Peak Daily Demand"
        value={formatDecimal(data?.peak_daily_demand)}
        unit={data?.peak_daily_demand != null ? "units" : undefined}
        helperText={data?.peak_date ? `on ${formatDate(data.peak_date)}` : undefined}
        loading={isLoading}
        tooltip="The single highest observed daily demand."
      />
      <MetricCard
        label="Dominant ATC Class"
        value={data?.dominant_atc_class ?? "Not available"}
        helperText={dominantShare}
        loading={isLoading}
        tooltip="The ATC class with the largest share of total observed demand."
      />
    </div>
  );
}
