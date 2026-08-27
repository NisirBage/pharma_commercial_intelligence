import type { UseQueryResult } from "@tanstack/react-query";
import { Area, CartesianGrid, ComposedChart, Line, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { ChartCard } from "../../components/charts/ChartCard";
import { ChartLegend } from "../../components/charts/ChartLegend";
import { ChartTooltip } from "../../components/charts/ChartTooltip";
import { CHART_CHROME, CHART_SERIES_COLORS } from "../../components/charts/chartTheme";
import { EmptyState } from "../../components/ui/EmptyState/EmptyState";
import { ErrorState } from "../../components/ui/ErrorState/ErrorState";
import { Skeleton } from "../../components/ui/Skeleton/Skeleton";
import { Table, type TableColumn } from "../../components/ui/Table/Table";
import { formatDate, formatDecimal } from "../../lib/format";
import type { ForecastResponse, SalesTrends } from "../../types/api";
import styles from "./Forecasting.module.css";

export interface ForecastChartProps {
  forecastQuery: UseQueryResult<ForecastResponse, unknown>;
  historyQuery: UseQueryResult<SalesTrends, unknown>;
  /** How many trailing days of history to show alongside the forecast —
   * a display-window choice, not a backend parameter (the trends
   * endpoint has none for "recent"; see docs/frontend-forecasting-
   * intelligence-page.md for why the full series is fetched and
   * sliced client-side rather than requesting a bounded range). */
  historyWindowDays: number;
}

interface CombinedPoint {
  date: string;
  observed?: number;
  prediction?: number;
  /** [lower, upper] — Recharts renders a two-value dataKey as a filled
   * band directly, which is how the confidence interval is drawn. */
  range?: [number, number];
}

const columns: TableColumn<CombinedPoint>[] = [
  { key: "date", header: "Date", render: (row) => formatDate(row.date) },
  { key: "type", header: "Type", render: (row) => (row.observed !== undefined ? "Historical" : "Forecast") },
  { key: "observed", header: "Observed", align: "end", render: (row) => (row.observed !== undefined ? formatDecimal(row.observed) : "—") },
  { key: "prediction", header: "Prediction", align: "end", render: (row) => (row.prediction !== undefined ? formatDecimal(row.prediction) : "—") },
  {
    key: "interval",
    header: "Confidence Interval",
    align: "end",
    render: (row) => (row.range ? `${formatDecimal(row.range[0])} – ${formatDecimal(row.range[1])}` : "—"),
  },
];

/** The primary forecast visualization: recent historical actuals
 * (GET /api/v1/sales/trends) joined with the forecast series (GET
 * /api/v1/forecast/{...}) into one continuous timeline, plus the
 * returned confidence interval — never a fabricated one. Historical
 * and forecast are distinguished both visually (color/line style, per
 * chartTheme's observed/forecast roles) and structurally (a
 * ReferenceLine + label at the boundary, a "Type" column in the
 * accessible table), never by color alone. */
export function ForecastChart({ forecastQuery, historyQuery, historyWindowDays }: ForecastChartProps) {
  const isLoading = forecastQuery.isLoading || historyQuery.isLoading;
  const isError = forecastQuery.isError || historyQuery.isError;

  if (isError) {
    return (
      <ErrorState
        title="Couldn't load the forecast"
        error={forecastQuery.error ?? historyQuery.error}
        onRetry={() => {
          forecastQuery.refetch();
          historyQuery.refetch();
        }}
      />
    );
  }

  if (isLoading) {
    return (
      <ChartCard title="Demand: Historical vs. Forecast" subtitle="Loading…">
        <Skeleton variant="chart" />
      </ChartCard>
    );
  }

  const forecast = forecastQuery.data;
  if (!forecast || forecast.forecast.length === 0) {
    return <EmptyState title="No forecast available" description="The API returned no forecast points for this selection." />;
  }

  const historyPoints = (historyQuery.data?.points ?? []).slice(-historyWindowDays);
  const forecastStartDate = forecast.forecast[0]!.date;

  const combined: CombinedPoint[] = [
    ...historyPoints.map((p) => ({ date: p.period, observed: p.units_sold ?? undefined })),
    ...forecast.forecast.map((p) => ({
      date: p.date,
      prediction: p.prediction ?? undefined,
      range: p.lower != null && p.upper != null ? ([p.lower, p.upper] as [number, number]) : undefined,
    })),
  ];

  const hasInterval = forecast.forecast.some((p) => p.lower != null && p.upper != null);
  const legendItems = [
    { label: "Historical", color: CHART_SERIES_COLORS.observed, variant: "line" as const },
    { label: "Forecast", color: CHART_SERIES_COLORS.forecast, variant: "line" as const },
    ...(hasInterval ? [{ label: "Confidence interval", color: CHART_SERIES_COLORS.interval, variant: "area" as const }] : []),
  ];

  return (
    <div className={styles.sectionStack}>
      <ChartCard
        title="Demand: Historical vs. Forecast"
        subtitle={`${forecast.atc_class === "ALL" ? "All classes" : forecast.atc_class} · ${forecast.model} · ${forecast.horizon_days}-day horizon`}
        footer={<ChartLegend items={legendItems} />}
      >
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={combined} margin={{ left: 8, right: 16, top: 8, bottom: 8 }} accessibilityLayer>
            <CartesianGrid vertical={false} stroke={CHART_CHROME.grid} />
            <XAxis
              dataKey="date"
              interval={Math.max(0, Math.ceil(combined.length / 10) - 1)}
              tickFormatter={(value: string) => formatDate(value)}
              stroke={CHART_CHROME.axis}
              fontSize={12}
            />
            <YAxis stroke={CHART_CHROME.axis} fontSize={12} width={56} />
            <Tooltip
              content={({ active, label, payload }) => (
                <ChartTooltip
                  active={active}
                  label={typeof label === "string" ? formatDate(label) : label}
                  payload={payload
                    ?.filter((p) => p.value !== undefined && p.dataKey !== "range")
                    .map((p) => ({
                      name: p.dataKey === "observed" ? "Historical" : "Forecast",
                      value: formatDecimal(Array.isArray(p.value) ? p.value[0] : (p.value as number)),
                      color: p.dataKey === "observed" ? CHART_SERIES_COLORS.observed : CHART_SERIES_COLORS.forecast,
                    }))}
                />
              )}
            />
            {hasInterval && (
              <Area
                dataKey="range"
                name="Confidence interval"
                stroke="none"
                fill={CHART_SERIES_COLORS.interval}
                fillOpacity={0.5}
                isAnimationActive={false}
              />
            )}
            <Line
              type="monotone"
              dataKey="observed"
              name="Historical"
              stroke={CHART_SERIES_COLORS.observed}
              strokeWidth={2}
              dot={false}
              connectNulls={false}
            />
            <Line
              type="monotone"
              dataKey="prediction"
              name="Forecast"
              stroke={CHART_SERIES_COLORS.forecast}
              strokeWidth={2}
              strokeDasharray="5 3"
              dot={false}
              connectNulls={false}
            />
            <ReferenceLine
              x={forecastStartDate}
              stroke={CHART_CHROME.axis}
              strokeDasharray="3 3"
              label={{ value: "Forecast begins", position: "insideTopLeft", fill: CHART_CHROME.axisLabel, fontSize: 11 }}
            />
          </ComposedChart>
        </ResponsiveContainer>
      </ChartCard>

      <Table
        caption="Historical and forecast demand by date, including the confidence interval where available"
        columns={columns}
        rows={combined}
        rowKey={(row) => row.date}
        density="compact"
      />
    </div>
  );
}
