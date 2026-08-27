import { useState } from "react";
import { ArrowDown, ArrowUp } from "lucide-react";
import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { ChartCard } from "../../components/charts/ChartCard";
import { ChartTooltip } from "../../components/charts/ChartTooltip";
import { CHART_CHROME, CHART_STATUS_COLORS } from "../../components/charts/chartTheme";
import { Badge } from "../../components/ui/Badge/Badge";
import { DateRange } from "../../components/ui/DateRange/DateRange";
import { EmptyState } from "../../components/ui/EmptyState/EmptyState";
import { ErrorState } from "../../components/ui/ErrorState/ErrorState";
import { MetricCard } from "../../components/ui/MetricCard/MetricCard";
import { SectionHeader } from "../../components/ui/SectionHeader/SectionHeader";
import { Select } from "../../components/ui/Select/Select";
import { Skeleton } from "../../components/ui/Skeleton/Skeleton";
import { Table, type TableColumn } from "../../components/ui/Table/Table";
import { useAnomalies } from "../../hooks/useAnomalies";
import { getAnomalySeverityDisplay } from "../../lib/domainLabels";
import { formatDate, formatDecimal, formatPercent } from "../../lib/format";
import type { AnomalyItem, AnomalyMethod } from "../../types/api";
import { ATC_SELECT_OPTIONS, toAtcClassParam } from "./atcOptions";
import styles from "./DemandIntelligence.module.css";

const METHOD_OPTIONS: { value: AnomalyMethod; label: string }[] = [
  { value: "rolling_zscore", label: "Rolling z-score" },
  { value: "iqr", label: "IQR (Tukey fence)" },
];

const SEVERITY_OPTIONS = [
  { value: "", label: "Any severity" },
  { value: "low", label: "Low" },
  { value: "medium", label: "Medium" },
  { value: "high", label: "High" },
];

const SEVERITY_SCORE_COLOR: Record<string, string> = {
  low: CHART_CHROME.axisLabel,
  medium: CHART_STATUS_COLORS.warning,
  high: CHART_STATUS_COLORS.danger,
};

/** Cap on how many anomaly records are rendered as chart bars/table
 * rows — see the comment in AnomaliesSection above. */
const DISPLAY_LIMIT = 100;

const SEVERITY_RANK: Record<string, number> = { high: 3, medium: 2, low: 1 };

function rankAnomaly(a: AnomalyItem, b: AnomalyItem): number {
  const severityDiff = (SEVERITY_RANK[b.severity] ?? 0) - (SEVERITY_RANK[a.severity] ?? 0);
  if (severityDiff !== 0) return severityDiff;
  return Math.abs(b.anomaly_score ?? 0) - Math.abs(a.anomaly_score ?? 0);
}

const columns: TableColumn<AnomalyItem>[] = [
  { key: "timestamp", header: "Date", render: (row) => formatDate(row.timestamp) },
  { key: "atc_class", header: "ATC Class", render: (row) => row.atc_class },
  { key: "observed", header: "Observed", align: "end", render: (row) => formatDecimal(row.observed) },
  { key: "expected", header: "Expected", align: "end", render: (row) => formatDecimal(row.expected) },
  { key: "deviation", header: "Deviation", align: "end", render: (row) => formatPercent(row.deviation_pct) },
  {
    key: "direction",
    header: "Direction",
    render: (row) => (
      <span className={styles.directionCell}>
        {row.direction === "above" ? <ArrowUp size={14} aria-hidden="true" /> : <ArrowDown size={14} aria-hidden="true" />}
        {row.direction === "above" ? "Above expected" : "Below expected"}
      </span>
    ),
  },
  {
    key: "severity",
    header: "Severity",
    render: (row) => {
      const severity = getAnomalySeverityDisplay(row.severity);
      return <Badge variant={severity.variant}>{severity.label}</Badge>;
    },
  },
];

/** Where are the unusual demand observations? GET
 * /api/v1/analytics/anomalies — the backend's rolling-z-score/IQR
 * detection and severity classification, read directly. No overlay
 * onto a separately-fetched trend line (M7.5 Sec. 8's explicit
 * fallback: "if overlaying markers becomes too complex or misleading,
 * use a ranked/table view") — instead a direct chart of the anomalies'
 * own returned values (deviation %) plus the full table. */
export function AnomaliesSection() {
  const [atcSelectValue, setAtcSelectValue] = useState("");
  const [method, setMethod] = useState<AnomalyMethod>("rolling_zscore");
  const [severity, setSeverity] = useState("");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");

  const atcClass = toAtcClassParam(atcSelectValue);
  const { data, isLoading, isError, error, refetch } = useAnomalies({
    atcClass,
    method,
    severity: severity || undefined,
    startDate: startDate || undefined,
    endDate: endDate || undefined,
  });

  // The endpoint has no server-side limit/pagination — an unfiltered
  // aggregate scan can return 1,000+ records (verified against the
  // real backend). Rendering all of them as DOM table rows and chart
  // bars is exactly the "massive DOM table" M7.5 Sec. 18 warns
  // against, so this ranks by severity (most concerning first — a
  // sort of already-computed fields, not a new statistic) and caps
  // what's rendered, while `total_count` above always shows the true,
  // untruncated figure and the existing ATC/severity/date filters are
  // how a user narrows further.
  const displayedAnomalies = data ? [...data.anomalies].sort(rankAnomaly).slice(0, DISPLAY_LIMIT) : [];
  const isTruncated = data ? data.anomalies.length > DISPLAY_LIMIT : false;
  // The table's severity-first order isn't a sensible x-axis order for
  // the chart (a date axis with scrambled dates is unreadable/
  // misleading) — same selected subset, re-sorted chronologically just
  // for the chart.
  const chartAnomalies = [...displayedAnomalies].sort((a, b) => a.timestamp.localeCompare(b.timestamp));

  return (
    <div className={styles.sectionStack}>
      <SectionHeader
        id="anomalies-heading"
        eyebrow="Step 4"
        title="Anomalies"
        description="Demand observations flagged as statistically unusual, by detection method."
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
            label="Detection method"
            options={METHOD_OPTIONS}
            value={method}
            onChange={(e) => setMethod(e.target.value as AnomalyMethod)}
          />
        </div>
        <div className={styles.filterField}>
          <Select
            label="Severity"
            options={SEVERITY_OPTIONS}
            value={severity}
            onChange={(e) => setSeverity(e.target.value)}
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
        <ErrorState title="Couldn't load anomalies" error={error} onRetry={() => refetch()} />
      ) : isLoading ? (
        <>
          <MetricCard label="Anomalies Detected" loading />
          <ChartCard title="Anomaly Deviation by Date">
            <Skeleton variant="chart" />
          </ChartCard>
          <Skeleton variant="table" count={5} />
        </>
      ) : !data ? (
        <EmptyState title="No anomaly data available" />
      ) : data.anomalies.length === 0 ? (
        <>
          <MetricCard label="Anomalies Detected" value="0" />
          <EmptyState
            title="No anomalies for this selection"
            description="No observations were flagged for the chosen ATC class, method, severity, and date range."
          />
        </>
      ) : (
        <>
          <MetricCard
            label="Anomalies Detected"
            value={String(data.total_count)}
            helperText={`${data.atc_class ?? "All ATC classes"} · ${METHOD_OPTIONS.find((m) => m.value === data.method)?.label ?? data.method}`}
          />

          {isTruncated && (
            <p className={styles.unavailableNote}>
              Showing the {DISPLAY_LIMIT} most severe of {data.total_count} anomalies. Narrow by ATC class, severity,
              or date range to see the full set.
            </p>
          )}

          <ChartCard
            title="Anomaly Deviation by Date"
            subtitle="Percent deviation from expected demand, colored by severity"
          >
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chartAnomalies} margin={{ left: 8, right: 16, top: 8, bottom: 8 }} accessibilityLayer>
                <CartesianGrid vertical={false} stroke={CHART_CHROME.grid} />
                <XAxis
                  dataKey="timestamp"
                  tickFormatter={(value: string) => formatDate(value)}
                  stroke={CHART_CHROME.axis}
                  fontSize={12}
                />
                <YAxis
                  stroke={CHART_CHROME.axis}
                  fontSize={12}
                  width={56}
                  tickFormatter={(value: number) => `${value}%`}
                />
                <Tooltip
                  content={({ active, label, payload }) => (
                    <ChartTooltip
                      active={active}
                      label={typeof label === "string" ? formatDate(label) : label}
                      payload={payload?.map((p) => ({
                        name: "Deviation",
                        value: formatPercent(p.value as number),
                        color: SEVERITY_SCORE_COLOR[(p.payload as AnomalyItem).severity] ?? CHART_CHROME.axis,
                      }))}
                    />
                  )}
                />
                <Bar dataKey="deviation_pct" name="Deviation">
                  {chartAnomalies.map((item, index) => (
                    <Cell key={`${item.atc_class}-${item.timestamp}-${index}`} fill={SEVERITY_SCORE_COLOR[item.severity] ?? CHART_CHROME.axis} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </ChartCard>

          <Table
            caption="Flagged anomalies: date, ATC class, observed vs. expected demand, deviation, direction, and severity"
            columns={columns}
            rows={displayedAnomalies}
            rowKey={(row) => `${row.atc_class}-${row.timestamp}-${row.method}`}
            density="compact"
          />
        </>
      )}
    </div>
  );
}
