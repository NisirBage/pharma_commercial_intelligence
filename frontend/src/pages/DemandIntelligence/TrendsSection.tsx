import { useMemo, useState } from "react";
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { ChartCard } from "../../components/charts/ChartCard";
import { ChartTooltip } from "../../components/charts/ChartTooltip";
import { CHART_CHROME, CHART_SERIES_COLORS } from "../../components/charts/chartTheme";
import { DateRange } from "../../components/ui/DateRange/DateRange";
import { EmptyState } from "../../components/ui/EmptyState/EmptyState";
import { ErrorState } from "../../components/ui/ErrorState/ErrorState";
import { MetricCard } from "../../components/ui/MetricCard/MetricCard";
import { SectionHeader } from "../../components/ui/SectionHeader/SectionHeader";
import { Select } from "../../components/ui/Select/Select";
import { Skeleton } from "../../components/ui/Skeleton/Skeleton";
import { useSalesTrends } from "../../hooks/useSalesTrends";
import { formatCount, formatDate, formatDecimal } from "../../lib/format";
import type { Grain } from "../../types/api";
import { ATC_SELECT_OPTIONS, toAtcClassParam } from "./atcOptions";
import styles from "./DemandIntelligence.module.css";

const GRAIN_OPTIONS: { value: Grain; label: string }[] = [
  { value: "daily", label: "Daily" },
  { value: "weekly", label: "Weekly" },
  { value: "monthly", label: "Monthly" },
];

/** How has demand changed over time? GET /api/v1/sales/trends,
 * filterable by ATC class / grain / date range — all three map
 * directly to backend query parameters, never invented client-side. */
export function TrendsSection() {
  const [atcSelectValue, setAtcSelectValue] = useState("");
  const [grain, setGrain] = useState<Grain>("daily");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");

  const atcClass = toAtcClassParam(atcSelectValue);
  const query = useSalesTrends({
    atcClass,
    grain,
    startDate: startDate || undefined,
    endDate: endDate || undefined,
  });
  const { data, isLoading, isError, error, refetch } = query;

  // Display-only aggregates over the points this exact query returned
  // — a plain mean/max of already-rendered data, not a new statistic
  // (M7.5 Sec. 3 permits "simple presentation operations"; this is not
  // regression, trend classification, or anything M3 already computes
  // for a *different* purpose than "summarize what's on screen").
  const summary = useMemo(() => {
    const points = data?.points ?? [];
    const values = points.map((p) => p.units_sold).filter((v): v is number => v != null);
    if (values.length === 0) return null;
    const sum = values.reduce((acc, v) => acc + v, 0);
    return {
      count: points.length,
      average: sum / values.length,
      peak: Math.max(...values),
    };
  }, [data]);

  // Avoid an unreadable wall of x-axis labels for ~2,100 daily points
  // across the full period — a fixed label budget, not a data change.
  const tickInterval = data && data.points.length > 10 ? Math.ceil(data.points.length / 8) : 0;

  return (
    <div className={styles.sectionStack}>
      <SectionHeader
        id="trends-heading"
        eyebrow="Step 1"
        title="Demand Trends"
        description="Observed demand over time, at the grain and ATC class you choose."
      />

      <div className={styles.filterBar}>
        <div className={styles.filterField}>
          <Select
            label="ATC class"
            options={ATC_SELECT_OPTIONS}
            value={atcSelectValue}
            onChange={(e) => setAtcSelectValue(e.target.value)}
          />
        </div>
        <div className={styles.filterField}>
          <Select
            label="Grain"
            options={GRAIN_OPTIONS}
            value={grain}
            onChange={(e) => setGrain(e.target.value as Grain)}
          />
        </div>
        <DateRange
          startLabel="From"
          endLabel="To"
          startValue={startDate}
          endValue={endDate}
          onStartChange={setStartDate}
          onEndChange={setEndDate}
        />
      </div>

      {isError ? (
        <ErrorState title="Couldn't load demand trends" error={error} onRetry={() => refetch()} />
      ) : isLoading ? (
        <ChartCard title="Observed Demand" subtitle="Loading…">
          <Skeleton variant="chart" />
        </ChartCard>
      ) : !data || data.points.length === 0 ? (
        <EmptyState
          title="No demand data for this selection"
          description="Try a different ATC class, grain, or date range."
        />
      ) : (
        <>
          <ChartCard
            title="Observed Demand"
            subtitle={`${data.atc_class ?? "All classes"} · ${grain} · ${formatDate(data.start_date)} – ${formatDate(data.end_date)}`}
          >
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={data.points} margin={{ left: 8, right: 16, top: 8, bottom: 8 }} accessibilityLayer>
                <CartesianGrid vertical={false} stroke={CHART_CHROME.grid} />
                <XAxis
                  dataKey="period"
                  interval={tickInterval}
                  tickFormatter={(value: string) => formatDate(value)}
                  stroke={CHART_CHROME.axis}
                  fontSize={12}
                />
                <YAxis
                  stroke={CHART_CHROME.axis}
                  fontSize={12}
                  tickFormatter={(value: number) => formatCount(value, true)}
                  width={56}
                />
                <Tooltip
                  content={({ active, label, payload }) => (
                    <ChartTooltip
                      active={active}
                      label={typeof label === "string" ? formatDate(label) : label}
                      payload={payload?.map((p) => ({
                        name: "Units sold",
                        value: formatDecimal(p.value as number),
                        color: CHART_SERIES_COLORS.observed,
                      }))}
                    />
                  )}
                />
                <Line
                  type="monotone"
                  dataKey="units_sold"
                  name="Units sold"
                  stroke={CHART_SERIES_COLORS.observed}
                  dot={data.points.length <= 60}
                  strokeWidth={2}
                />
              </LineChart>
            </ResponsiveContainer>
          </ChartCard>

          {summary && (
            <div className={styles.summaryGrid}>
              <MetricCard label="ATC Class" value={data.atc_class ?? "All classes"} />
              <MetricCard label="Grain" value={GRAIN_OPTIONS.find((g) => g.value === grain)?.label ?? grain} />
              <MetricCard
                label="Observations"
                value={formatCount(summary.count)}
                helperText="Points in this view"
              />
              <MetricCard
                label="Avg / Peak (this view)"
                value={formatDecimal(summary.average)}
                helperText={`Peak ${formatDecimal(summary.peak)} — computed from the points shown above`}
              />
            </div>
          )}
        </>
      )}
    </div>
  );
}
