import { useState } from "react";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { ChartCard } from "../../components/charts/ChartCard";
import { ChartTooltip } from "../../components/charts/ChartTooltip";
import { CHART_CHROME, CHART_SERIES_COLORS } from "../../components/charts/chartTheme";
import { EmptyState } from "../../components/ui/EmptyState/EmptyState";
import { ErrorState } from "../../components/ui/ErrorState/ErrorState";
import { MetricCard } from "../../components/ui/MetricCard/MetricCard";
import { SectionHeader } from "../../components/ui/SectionHeader/SectionHeader";
import { Select } from "../../components/ui/Select/Select";
import { useSeasonality } from "../../hooks/useSeasonality";
import { formatDecimal, formatPValue, formatStrength } from "../../lib/format";
import type { DayOfWeekEffect, HourOfDayEffect } from "../../types/api";
import { ATC_SELECT_OPTIONS, toAtcClassParam } from "../../lib/atcOptions";
import styles from "./DemandIntelligence.module.css";

// A fixed calendar-order display convention only — the backend's
// mean_units_by_weekday is a plain dict with no guaranteed key order,
// so this reorders for readability without inventing any value.
const WEEKDAY_ORDER = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];

/** What seasonal patterns recur? GET /api/v1/analytics/seasonality —
 * every statistic (Kruskal-Wallis day-of-week/hour-of-day effect, STL
 * seasonal strength) is M3's, read directly; this section never
 * computes or guesses one, and an `available: false` metric always
 * shows the API's own `reason`, never a substitute value. */
export function SeasonalitySection() {
  const [atcSelectValue, setAtcSelectValue] = useState("");
  const atcClass = toAtcClassParam(atcSelectValue);
  const { data, isLoading, isError, error, refetch } = useSeasonality(atcClass);

  return (
    <div className={styles.sectionStack}>
      <SectionHeader
        id="seasonality-heading"
        eyebrow="Step 3"
        title="Seasonality"
        description="Recurring weekly, hourly, and annual demand patterns."
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
      </div>

      {isError ? (
        <ErrorState title="Couldn't load seasonality data" error={error} onRetry={() => refetch()} />
      ) : isLoading ? (
        <div className={styles.summaryGridNarrow}>
          <MetricCard label="Weekly Seasonal Strength" loading />
          <MetricCard label="Annual Seasonal Strength" loading />
        </div>
      ) : !data ? (
        <EmptyState title="No seasonality data available" />
      ) : (
        <>
          <div className={styles.summaryGridNarrow}>
            <MetricCard
              label="Weekly Seasonal Strength"
              value={data.weekly_seasonal_strength.available ? formatStrength(data.weekly_seasonal_strength.strength) : "Not available"}
              helperText={
                data.weekly_seasonal_strength.available
                  ? (data.weekly_seasonal_strength.interpretation ?? undefined)
                  : (data.weekly_seasonal_strength.reason ?? undefined)
              }
            />
            <MetricCard
              label="Annual Seasonal Strength"
              value={data.annual_seasonal_strength.available ? formatStrength(data.annual_seasonal_strength.strength) : "Not available"}
              helperText={
                data.annual_seasonal_strength.available
                  ? (data.annual_seasonal_strength.interpretation ?? undefined)
                  : (data.annual_seasonal_strength.reason ?? undefined)
              }
            />
          </div>

          <DayOfWeekChart effect={data.day_of_week_effect} />
          <HourOfDayChart effect={data.hour_of_day_effect} />
        </>
      )}
    </div>
  );
}

function DayOfWeekChart({ effect }: { effect: DayOfWeekEffect }) {
  if (!effect.available || !effect.mean_units_by_weekday) {
    return (
      <ChartCard title="Day-of-Week Effect" subtitle="Kruskal-Wallis test on daily total demand">
        <EmptyState
          title="Not available"
          description={effect.reason ?? "The API did not report a reason."}
        />
      </ChartCard>
    );
  }

  const byDay = effect.mean_units_by_weekday;
  const rows = WEEKDAY_ORDER.filter((day) => day in byDay).map((day) => ({ day, value: byDay[day]! }));

  return (
    <ChartCard
      title="Day-of-Week Effect"
      subtitle={`Mean daily demand by weekday — ${effect.significant ? "statistically significant" : "not statistically significant"} (${formatPValue(effect.p_value)})`}
    >
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={rows} margin={{ left: 8, right: 16, top: 8, bottom: 8 }} accessibilityLayer>
          <CartesianGrid vertical={false} stroke={CHART_CHROME.grid} />
          <XAxis dataKey="day" stroke={CHART_CHROME.axis} fontSize={12} tickFormatter={(d: string) => d.slice(0, 3)} />
          <YAxis stroke={CHART_CHROME.axis} fontSize={12} width={48} />
          <Tooltip
            content={({ active, label, payload }) => (
              <ChartTooltip
                active={active}
                label={label}
                payload={payload?.map((p) => ({
                  name: "Mean demand",
                  value: formatDecimal(p.value as number),
                  color: CHART_SERIES_COLORS.observed,
                }))}
              />
            )}
          />
          <Bar dataKey="value" name="Mean demand" fill={CHART_SERIES_COLORS.observed} radius={[4, 4, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </ChartCard>
  );
}

function HourOfDayChart({ effect }: { effect: HourOfDayEffect }) {
  if (!effect.available || !effect.mean_units_by_hour) {
    return (
      <ChartCard title="Hour-of-Day Effect" subtitle="Kruskal-Wallis test on hourly demand">
        <EmptyState
          title="Not available"
          description={effect.reason ?? "The API did not report a reason."}
        />
      </ChartCard>
    );
  }

  const byHour = effect.mean_units_by_hour;
  const rows = Object.keys(byHour)
    .map(Number)
    .sort((a, b) => a - b)
    .map((hour) => ({ hour: `${hour}:00`, value: byHour[String(hour)]! }));

  return (
    <ChartCard
      title="Hour-of-Day Effect"
      subtitle={`Mean hourly demand — ${effect.significant ? "statistically significant" : "not statistically significant"} (${formatPValue(effect.p_value)})`}
    >
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={rows} margin={{ left: 8, right: 16, top: 8, bottom: 8 }} accessibilityLayer>
          <CartesianGrid vertical={false} stroke={CHART_CHROME.grid} />
          <XAxis dataKey="hour" stroke={CHART_CHROME.axis} fontSize={12} interval={rows.length > 12 ? 1 : 0} />
          <YAxis stroke={CHART_CHROME.axis} fontSize={12} width={48} />
          <Tooltip
            content={({ active, label, payload }) => (
              <ChartTooltip
                active={active}
                label={label}
                payload={payload?.map((p) => ({
                  name: "Mean demand",
                  value: formatDecimal(p.value as number),
                  color: CHART_SERIES_COLORS.forecast,
                }))}
              />
            )}
          />
          <Bar dataKey="value" name="Mean demand" fill={CHART_SERIES_COLORS.forecast} radius={[4, 4, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </ChartCard>
  );
}
