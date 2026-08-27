import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { ChartCard } from "../../components/charts/ChartCard";
import { ChartTooltip } from "../../components/charts/ChartTooltip";
import { CHART_CHROME, CHART_SERIES_COLORS } from "../../components/charts/chartTheme";
import { Badge } from "../../components/ui/Badge/Badge";
import { EmptyState } from "../../components/ui/EmptyState/EmptyState";
import { ErrorState } from "../../components/ui/ErrorState/ErrorState";
import { MetricCard } from "../../components/ui/MetricCard/MetricCard";
import { SectionHeader } from "../../components/ui/SectionHeader/SectionHeader";
import { Skeleton } from "../../components/ui/Skeleton/Skeleton";
import { Table, type TableColumn } from "../../components/ui/Table/Table";
import { useAtcAnalytics } from "../../hooks/useAtcAnalytics";
import { getTrendDisplay } from "../../lib/domainLabels";
import { formatCount, formatCV, formatDecimal, formatPValue, formatPercent } from "../../lib/format";
import type { AtcPerformance } from "../../types/api";
import styles from "./DemandIntelligence.module.css";

const columns: TableColumn<AtcPerformance>[] = [
  { key: "atc_class", header: "ATC Class", render: (row) => row.atc_class },
  { key: "total_demand", header: "Total Demand", align: "end", render: (row) => formatCount(row.total_demand) },
  { key: "contribution", header: "Contribution", align: "end", render: (row) => formatPercent(row.contribution_pct) },
  { key: "avg_daily", header: "Avg Daily", align: "end", render: (row) => formatDecimal(row.average_daily_demand) },
  { key: "volatility", header: "Volatility (CV)", align: "end", render: (row) => formatCV(row.volatility_cv) },
  {
    key: "trend",
    header: "Trend",
    render: (row) => {
      const trend = getTrendDisplay(row.trend_classification);
      return <Badge variant={trend.variant}>{trend.label}</Badge>;
    },
  },
  { key: "p_value", header: "Significance", align: "end", render: (row) => formatPValue(row.trend_p_value) },
];

/** Which therapeutic classes drive demand, and how are they behaving?
 * GET /api/v1/analytics/atc — the same endpoint and per-class fields
 * M7.4's Overview already consumes; TanStack Query's cache means
 * navigating here right after Overview is typically an instant hit,
 * not a second network round trip. */
export function AtcAnalysisSection() {
  const { data, isLoading, isError, error, refetch } = useAtcAnalytics();

  return (
    <div className={styles.sectionStack}>
      <SectionHeader
        id="atc-heading"
        eyebrow="Step 2"
        title="ATC Analysis"
        description="Contribution, trend, and volatility for each observed ATC class."
      />

      {isError ? (
        <ErrorState title="Couldn't load ATC analytics" error={error} onRetry={() => refetch()} />
      ) : isLoading ? (
        <>
          <ChartCard title="Demand Contribution by ATC Class">
            <Skeleton variant="chart" />
          </ChartCard>
          <Skeleton variant="table" count={8} />
        </>
      ) : !data || data.classes.length === 0 ? (
        <EmptyState title="No ATC class data available" description="The API returned no ATC class performance records." />
      ) : (
        <>
          <div className={styles.summaryGridNarrow}>
            <MetricCard
              label="Top 3 Classes (CR3)"
              value={formatPercent(data.concentration.concentration_ratio_top3_pct)}
              tooltip="Combined demand share of the 3 largest ATC classes."
            />
            <MetricCard
              label="HHI"
              value={data.concentration.hhi != null ? data.concentration.hhi.toFixed(1) : "Not available"}
              tooltip={data.concentration.hhi_scale_note}
            />
          </div>

          <ChartCard
            title="Demand Contribution by ATC Class"
            subtitle="Ranked by share of total observed demand"
            height={Math.max(240, data.classes.length * 40)}
          >
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                data={[...data.classes].sort((a, b) => (b.contribution_pct ?? 0) - (a.contribution_pct ?? 0))}
                layout="vertical"
                margin={{ left: 8, right: 24, top: 8, bottom: 8 }}
                accessibilityLayer
              >
                <CartesianGrid horizontal={false} stroke={CHART_CHROME.grid} />
                <XAxis
                  type="number"
                  domain={[0, 100]}
                  tickFormatter={(value: number) => `${value}%`}
                  stroke={CHART_CHROME.axis}
                  fontSize={12}
                />
                <YAxis type="category" dataKey="atc_class" width={70} stroke={CHART_CHROME.axis} fontSize={12} />
                <Tooltip
                  cursor={{ fill: "rgba(17, 20, 27, 0.04)" }}
                  content={({ active, label, payload }) => (
                    <ChartTooltip
                      active={active}
                      label={label}
                      payload={payload?.map((p) => ({
                        name: "Contribution",
                        value: formatPercent(p.value as number),
                        color: CHART_SERIES_COLORS.forecast,
                      }))}
                    />
                  )}
                />
                <Bar dataKey="contribution_pct" name="Contribution" fill={CHART_SERIES_COLORS.forecast} radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </ChartCard>

          <Table
            caption="ATC class performance: total demand, contribution, average daily demand, volatility, and trend"
            columns={columns}
            rows={data.classes}
            rowKey={(row) => row.atc_class}
            density="compact"
          />
        </>
      )}
    </div>
  );
}
