import { useState } from "react";
import { CartesianGrid, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { ChartCard } from "../../components/charts/ChartCard";
import { ChartLegend } from "../../components/charts/ChartLegend";
import { ChartTooltip } from "../../components/charts/ChartTooltip";
import { CHART_CHROME, CHART_SERIES_COLORS } from "../../components/charts/chartTheme";
import { EmptyState } from "../../components/ui/EmptyState/EmptyState";
import { ErrorState } from "../../components/ui/ErrorState/ErrorState";
import { MetricCard } from "../../components/ui/MetricCard/MetricCard";
import { SectionHeader } from "../../components/ui/SectionHeader/SectionHeader";
import { Select } from "../../components/ui/Select/Select";
import { Skeleton } from "../../components/ui/Skeleton/Skeleton";
import { Table, type TableColumn } from "../../components/ui/Table/Table";
import { useOptimizationSensitivity } from "../../hooks/useOptimizationSensitivity";
import { ATC_ONLY_OPTIONS } from "../../lib/atcOptions";
import { formatCV, formatDecimal, formatFraction } from "../../lib/format";
import { ATC_CLASSES } from "../../types/api";
import type { ScenarioInfo, ScenarioName, SensitivityParameter, SensitivityPoint } from "../../types/api";
import styles from "./SupplyPlanning.module.css";

export interface SensitivitySectionProps {
  scenario: ScenarioName;
  scenarioInfo?: ScenarioInfo;
}

const PARAMETER_OPTIONS: { value: SensitivityParameter; label: string }[] = [
  { value: "service_level_target", label: "Service Level Target" },
  { value: "lead_time_days", label: "Lead Time" },
  { value: "demand_uncertainty_scale", label: "Demand Uncertainty Scale" },
  { value: "stockout_cost_weight", label: "Stockout Cost Weight" },
];

const PARAMETER_META: Record<SensitivityParameter, { unit: string; formatValue: (v: number) => string }> = {
  lead_time_days: { unit: "days", formatValue: (v) => `${v}` },
  service_level_target: { unit: "%", formatValue: (v) => formatFraction(v) },
  demand_uncertainty_scale: { unit: "x forecast-error std", formatValue: (v) => `${v}x` },
  stockout_cost_weight: { unit: "weight", formatValue: (v) => `${v}` },
};

/** The reference point each sweep is compared against. service_level_target
 * and lead_time_days come from the currently selected scenario (real,
 * API-sourced state); demand_uncertainty_scale's baseline is 1.0 by
 * definition (the sweep scales the actual forecast-error std by this
 * factor — 1.0 is "unscaled", see backend/app/optimization/sensitivity.py's
 * sweep_demand_uncertainty docstring); stockout_cost_weight's baseline
 * is 4.0, the single fixed value ALL 3 scenarios share (verified in
 * docs/planning-assumptions.md's assumption table — it does not vary by
 * scenario the way service_level_target does). The latter two are
 * frontend-derived reference points, not API fields — documented here
 * and in docs/frontend-supply-planning-optimization-page.md.
 */
function getBaselineValue(parameter: SensitivityParameter, scenarioInfo: ScenarioInfo | undefined): number | undefined {
  switch (parameter) {
    case "service_level_target":
      return scenarioInfo?.service_level_target;
    case "lead_time_days":
      return scenarioInfo?.lead_time_days;
    case "demand_uncertainty_scale":
      return 1.0;
    case "stockout_cost_weight":
      return 4.0;
    default:
      return undefined;
  }
}

const tableColumns: TableColumn<SensitivityPoint>[] = [
  { key: "value", header: "Swept Value", render: (row) => String(row.value) },
  { key: "safety_stock", header: "Safety Stock", align: "end", render: (row) => `${formatDecimal(row.safety_stock)} units` },
  { key: "reorder_point", header: "Reorder Point", align: "end", render: (row) => `${formatDecimal(row.reorder_point)} units` },
];

/** How sensitive is the recommendation to one input, holding the rest
 * of the current scenario fixed? GET /api/v1/optimization/sensitivity
 * — a single-class, single-parameter sweep; automatically fetched (no
 * separate "run" click — this is a GET, not the POST optimization run)
 * once an ATC class and parameter are chosen. */
export function SensitivitySection({ scenario, scenarioInfo }: SensitivitySectionProps) {
  const [atcClass, setAtcClass] = useState<string>(ATC_CLASSES[0]);
  const [parameter, setParameter] = useState<SensitivityParameter>("service_level_target");

  const { data, isLoading, isError, error, refetch } = useOptimizationSensitivity({ atcClass, scenario, parameter });

  const meta = PARAMETER_META[parameter];
  const baseline = getBaselineValue(parameter, scenarioInfo);

  return (
    <div className={styles.sectionStack}>
      <SectionHeader
        id="sensitivity-heading"
        eyebrow="Trade-offs"
        title="Sensitivity Analysis"
        description="How safety stock and reorder point respond to one planning assumption, holding the others fixed."
      />

      <div className={styles.controls}>
        <div className={styles.controlField}>
          <Select label="ATC class" options={ATC_ONLY_OPTIONS} value={atcClass} onChange={(e) => setAtcClass(e.target.value)} />
        </div>
        <div className={styles.controlField}>
          <Select
            label="Swept parameter"
            options={PARAMETER_OPTIONS}
            value={parameter}
            onChange={(e) => setParameter(e.target.value as SensitivityParameter)}
          />
        </div>
      </div>

      {isError ? (
        <ErrorState title="Couldn't load sensitivity data" error={error} onRetry={() => refetch()} />
      ) : isLoading ? (
        <ChartCard title="Sensitivity Sweep">
          <Skeleton variant="chart" />
        </ChartCard>
      ) : !data || data.points.length === 0 ? (
        <EmptyState title="No sensitivity data available" description="The API returned no points for this selection." />
      ) : (
        <>
          <div className={styles.sensitivityStats}>
            <MetricCard
              label="Elasticity"
              value={data.elasticity != null ? formatCV(data.elasticity) : "Not available"}
              tooltip="Endpoint-to-endpoint percent change in safety stock per percent change in the swept parameter — a comparable summary of how much this assumption moves the recommendation."
            />
            {baseline != null && (
              <MetricCard label="Current Baseline" value={meta.formatValue(baseline)} helperText={`This scenario's own ${PARAMETER_OPTIONS.find((p) => p.value === parameter)?.label.toLowerCase()}`} />
            )}
          </div>

          <ChartCard
            title="Sensitivity Sweep"
            subtitle={`${atcClass} · ${PARAMETER_OPTIONS.find((p) => p.value === parameter)?.label} (${meta.unit})`}
            footer={
              <ChartLegend
                items={[
                  { label: "Safety stock", color: CHART_SERIES_COLORS.forecast, variant: "line" },
                  { label: "Reorder point", color: CHART_SERIES_COLORS.observed, variant: "line" },
                ]}
              />
            }
          >
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={data.points} margin={{ left: 8, right: 16, top: 8, bottom: 8 }} accessibilityLayer>
                <CartesianGrid vertical={false} stroke={CHART_CHROME.grid} />
                <XAxis
                  dataKey="value"
                  type="number"
                  domain={["dataMin", "dataMax"]}
                  // Pin ticks to the actual swept grid values (5-6 real
                  // points, never many) rather than Recharts' default
                  // evenly-spaced numeric ticks, which don't align with
                  // the irregular grid this sweep actually uses (e.g.
                  // 0.8/0.9/0.95/0.98/0.99) — found during real-backend
                  // verification.
                  ticks={data.points.map((p) => p.value)}
                  tickFormatter={(v: number) => meta.formatValue(v)}
                  stroke={CHART_CHROME.axis}
                  fontSize={12}
                />
                <YAxis stroke={CHART_CHROME.axis} fontSize={12} width={56} />
                <Tooltip
                  content={({ active, label, payload }) => (
                    <ChartTooltip
                      active={active}
                      label={typeof label === "number" ? meta.formatValue(label) : label}
                      payload={payload?.map((p) => ({
                        name: p.dataKey === "safety_stock" ? "Safety stock" : "Reorder point",
                        value: formatDecimal(p.value as number),
                        color: p.dataKey === "safety_stock" ? CHART_SERIES_COLORS.forecast : CHART_SERIES_COLORS.observed,
                      }))}
                    />
                  )}
                />
                {baseline != null && (
                  <ReferenceLine
                    x={baseline}
                    stroke={CHART_CHROME.axis}
                    strokeDasharray="3 3"
                    label={{ value: "Current scenario", position: "insideTopLeft", fill: CHART_CHROME.axisLabel, fontSize: 11 }}
                  />
                )}
                <Line type="monotone" dataKey="safety_stock" name="Safety stock" stroke={CHART_SERIES_COLORS.forecast} strokeWidth={2} dot />
                <Line type="monotone" dataKey="reorder_point" name="Reorder point" stroke={CHART_SERIES_COLORS.observed} strokeWidth={2} dot />
              </LineChart>
            </ResponsiveContainer>
          </ChartCard>

          <Table
            caption="Sensitivity sweep: swept value, resulting safety stock, and reorder point"
            columns={tableColumns}
            rows={data.points}
            rowKey={(row) => String(row.value)}
            density="compact"
          />
        </>
      )}
    </div>
  );
}
