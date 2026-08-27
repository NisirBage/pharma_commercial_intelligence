import type { UseQueryResult } from "@tanstack/react-query";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { ChartCard } from "../../components/charts/ChartCard";
import { ChartTooltip } from "../../components/charts/ChartTooltip";
import { CHART_CHROME, CHART_SERIES_COLORS } from "../../components/charts/chartTheme";
import { EmptyState } from "../../components/ui/EmptyState/EmptyState";
import { ErrorState } from "../../components/ui/ErrorState/ErrorState";
import { MetricCard } from "../../components/ui/MetricCard/MetricCard";
import { SectionHeader } from "../../components/ui/SectionHeader/SectionHeader";
import { Skeleton } from "../../components/ui/Skeleton/Skeleton";
import { Table, type TableColumn } from "../../components/ui/Table/Table";
import { formatPercent } from "../../lib/format";
import type { AtcPerformanceResponse, ConcentrationEntry } from "../../types/api";
import styles from "./Overview.module.css";

export interface ConcentrationSectionProps {
  query: UseQueryResult<AtcPerformanceResponse, unknown>;
}

type RankedRow = ConcentrationEntry & { rank: number };

const columns: TableColumn<RankedRow>[] = [
  { key: "rank", header: "#", render: (row) => row.rank },
  { key: "atc_code", header: "ATC Class", render: (row) => row.atc_code },
  { key: "share", header: "Share", align: "end", render: (row) => formatPercent(row.share_pct) },
  { key: "cumulative", header: "Cumulative", align: "end", render: (row) => formatPercent(row.cumulative_share_pct) },
];

/** How concentrated demand is across the 8 observed ATC classes — a
 * horizontal bar chart (never a pie chart, per M7.4 Sec. 5) paired with
 * the same data as an accessible ranked table, plus the API's own CR3/
 * HHI figures. The HHI's reference-band interpretation is shown
 * verbatim from `hhi_scale_note` rather than the frontend picking a
 * band itself. */
export function ConcentrationSection({ query }: ConcentrationSectionProps) {
  const { data, isLoading, isError, error, refetch } = query;

  return (
    <section aria-labelledby="concentration-heading" className={styles.sectionStack}>
      <SectionHeader
        id="concentration-heading"
        eyebrow="Concentration"
        title="Demand Concentration"
        description="How concentrated observed demand is across the 8 ATC classes."
      />
      {isError ? (
        <ErrorState title="Couldn't load concentration data" error={error} onRetry={() => refetch()} />
      ) : (
        <>
          <div className={styles.concentrationStats}>
            <MetricCard
              label="Top 3 Classes (CR3)"
              value={formatPercent(data?.concentration.concentration_ratio_top3_pct)}
              loading={isLoading}
              tooltip="Combined demand share of the 3 largest ATC classes."
            />
            <MetricCard
              label="HHI"
              value={data?.concentration.hhi != null ? data.concentration.hhi.toFixed(1) : "Not available"}
              loading={isLoading}
              tooltip={data?.concentration.hhi_scale_note}
            />
          </div>

          {isLoading ? (
            <ChartCard title="Demand Share by ATC Class" subtitle="Ranked by contribution to total observed demand">
              <Skeleton variant="chart" />
            </ChartCard>
          ) : !data || data.concentration.ranked.length === 0 ? (
            <EmptyState
              title="No concentration data available"
              description="The API returned no ranked ATC classes for this dataset."
            />
          ) : (
            <>
              <ChartCard
                title="Demand Share by ATC Class"
                subtitle="Ranked by contribution to total observed demand"
                height={Math.max(240, data.concentration.ranked.length * 40)}
              >
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart
                    data={data.concentration.ranked}
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
                    <YAxis type="category" dataKey="atc_code" width={70} stroke={CHART_CHROME.axis} fontSize={12} />
                    <Tooltip
                      cursor={{ fill: "rgba(17, 20, 27, 0.04)" }}
                      content={({ active, label, payload }) => (
                        <ChartTooltip
                          active={active}
                          label={label}
                          payload={payload?.map((p) => ({
                            name: "Share of demand",
                            value: formatPercent(p.value as number),
                            color: CHART_SERIES_COLORS.forecast,
                          }))}
                        />
                      )}
                    />
                    <Bar dataKey="share_pct" name="Share of demand" fill={CHART_SERIES_COLORS.forecast} radius={[0, 4, 4, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </ChartCard>

              <Table
                caption="Ranked ATC classes by share of total observed demand, with cumulative share"
                columns={columns}
                rows={data.concentration.ranked.map((entry, index) => ({ ...entry, rank: index + 1 }))}
                rowKey={(row) => row.atc_code}
                density="compact"
              />
            </>
          )}
        </>
      )}
    </section>
  );
}
