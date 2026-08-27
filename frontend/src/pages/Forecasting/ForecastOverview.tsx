import type { UseQueryResult } from "@tanstack/react-query";
import { MetricCard } from "../../components/ui/MetricCard/MetricCard";
import { formatDate, formatDecimal, formatPercent } from "../../lib/format";
import type { ForecastResponse, SalesTrends } from "../../types/api";
import styles from "./Forecasting.module.css";

export interface ForecastOverviewProps {
  forecastQuery: UseQueryResult<ForecastResponse, unknown>;
  historyQuery: UseQueryResult<SalesTrends, unknown>;
}

/** Headline KPIs. "Expected Change" is the only derived figure here —
 * a plain percent change between the latest historical actual and the
 * mean forecast prediction, both already-returned values, computed
 * client-side, and explicitly labeled as such. Everything else is
 * read straight from the forecast response. */
export function ForecastOverview({ forecastQuery, historyQuery }: ForecastOverviewProps) {
  const isLoading = forecastQuery.isLoading || historyQuery.isLoading;
  const forecast = forecastQuery.data;
  const historyPoints = historyQuery.data?.points ?? [];
  const lastHistorical = [...historyPoints].reverse().find((p) => p.units_sold != null);

  const forecastValues = forecast?.forecast.map((p) => p.prediction).filter((v): v is number => v != null) ?? [];
  const avgForecast = forecastValues.length > 0 ? forecastValues.reduce((a, b) => a + b, 0) / forecastValues.length : null;

  const expectedChangePct =
    lastHistorical?.units_sold != null && avgForecast != null && lastHistorical.units_sold !== 0
      ? ((avgForecast - lastHistorical.units_sold) / lastHistorical.units_sold) * 100
      : null;

  return (
    <div className={styles.kpiGrid}>
      <MetricCard
        label="Latest Historical Demand"
        value={lastHistorical ? formatDecimal(lastHistorical.units_sold) : "Not available"}
        helperText={lastHistorical ? `on ${formatDate(lastHistorical.period)}` : undefined}
        loading={isLoading}
        tooltip="The most recent observed daily demand in the historical window shown below."
      />
      <MetricCard
        label="Avg Forecast Demand"
        value={avgForecast != null ? formatDecimal(avgForecast) : "Not available"}
        helperText={forecast ? `Mean of the ${forecast.horizon_days}-day forecast` : undefined}
        loading={isLoading}
        tooltip="Mean of the predicted values across the forecast horizon — computed from the points shown in the chart below, not an API field."
      />
      <MetricCard
        label="Expected Change"
        value={expectedChangePct != null ? formatPercent(expectedChangePct) : "Not available"}
        trend={expectedChangePct == null ? undefined : expectedChangePct > 0 ? "Increase" : expectedChangePct < 0 ? "Decrease" : "No change"}
        trendDirection={expectedChangePct == null ? undefined : expectedChangePct > 0 ? "up" : expectedChangePct < 0 ? "down" : "flat"}
        helperText="vs. latest observed demand"
        loading={isLoading}
        tooltip="Percent change from the latest historical observation to the average forecast value — a display-only comparison, not a model output."
      />
      <MetricCard
        label="Forecast Accuracy (WAPE)"
        value={forecast ? formatPercent(forecast.metrics.wape) : "Not available"}
        helperText="Weighted absolute percentage error, from backtesting"
        loading={isLoading}
        tooltip="Lower is better. Computed by M4's backtest, not this request — see Diagnostics below for the full accuracy picture."
      />
    </div>
  );
}
