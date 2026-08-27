import { AlertTriangle } from "lucide-react";
import { ApiError } from "../../api/client";
import { Badge } from "../../components/ui/Badge/Badge";
import { Card } from "../../components/ui/Card/Card";
import { EmptyState } from "../../components/ui/EmptyState/EmptyState";
import { ErrorState } from "../../components/ui/ErrorState/ErrorState";
import { MetricCard } from "../../components/ui/MetricCard/MetricCard";
import { SectionHeader } from "../../components/ui/SectionHeader/SectionHeader";
import { Table, type TableColumn } from "../../components/ui/Table/Table";
import { getSolverStatusDisplay } from "../../lib/domainLabels";
import { formatDecimal, formatNumber, formatPercent } from "../../lib/format";
import type { AssumptionRow, OptimizationRunResponse } from "../../types/api";
import styles from "./SupplyPlanning.module.css";

export interface OptimizationSummaryProps {
  /** The last SUCCESSFUL run's result — never cleared by a subsequent
   * failed run (see index.tsx's `lastSuccess` state). */
  result: OptimizationRunResponse | null;
  isPending: boolean;
  isError: boolean;
  error: unknown;
  /** True when the form's current values no longer match the
   * configuration that produced `result`. */
  isStale: boolean;
  onRetry: () => void;
}

function formatAssumptionValue(value: string | number | boolean | null): string {
  if (value === null) return "—";
  if (typeof value === "boolean") return value ? "Yes" : "No";
  if (typeof value === "number") return formatNumber(value);
  return value;
}

const assumptionColumns: TableColumn<AssumptionRow>[] = [
  { key: "parameter", header: "Parameter", render: (row) => row.parameter },
  { key: "value", header: "Value", align: "end", render: (row) => formatAssumptionValue(row.value) },
  { key: "unit", header: "Unit", render: (row) => row.unit },
  { key: "source", header: "Source", render: (row) => row.source },
  { key: "type", header: "Type", render: (row) => row.type },
];

/** The objective value and aggregate baseline-vs-optimized comparison
 * — the ONLY level at which a baseline comparison exists in the API
 * (per-class, only the optimized figures are returned; see
 * docs/frontend-supply-planning-optimization-page.md). */
export function OptimizationSummary({ result, isPending, isError, error, isStale, onRetry }: OptimizationSummaryProps) {
  const isInfeasible = error instanceof ApiError && error.code === "optimization_infeasible";

  if (!result && !isPending && !isError) {
    return (
      <EmptyState
        title="No optimization has been run yet"
        description="Choose a scenario above and click Run optimization to see a recommended safety-stock allocation."
      />
    );
  }

  return (
    <div className={styles.sectionStack}>
      <SectionHeader
        id="summary-heading"
        eyebrow="Result"
        title="Optimization Summary"
        description="The objective value achieved and how it compares with the naive equal-target baseline."
      />

      {isPending && (
        <p className={styles.staleNote} role="status">
          Running a new optimization{result ? " — the figures below are still from the previous run" : ""}…
        </p>
      )}

      {isError &&
        (isInfeasible ? (
          <ErrorState title="No feasible allocation found" message={error.message} onRetry={onRetry} />
        ) : (
          <ErrorState title="The optimization run failed" error={error} onRetry={onRetry} />
        ))}

      {result && (
        <>
          {isStale && !isPending && (
            <p className={styles.staleNote} role="status">
              The configuration above has changed since this result was computed — click Run optimization to update it.
            </p>
          )}

          <div className={styles.statusRow}>
            <span className={styles.statusLabel}>Solver status (optimized allocation)</span>
            <Badge variant={getSolverStatusDisplay(result.allocation_optimized.solver_status).variant}>
              {getSolverStatusDisplay(result.allocation_optimized.solver_status).label}
            </Badge>
          </div>

          {result.warnings.length > 0 && (
            <Card>
              <div className={styles.statusRow}>
                <AlertTriangle size={16} aria-hidden="true" />
                <span className={styles.statusLabel}>Warnings</span>
              </div>
              <ul className={styles.warningsList}>
                {result.warnings.map((warning) => (
                  <li key={warning}>{warning}</li>
                ))}
              </ul>
            </Card>
          )}

          <div className={styles.kpiGrid}>
            <MetricCard
              label="Shared Capacity Budget"
              value={formatDecimal(result.capacity_budget)}
              unit="units"
              tooltip="Total safety stock available to allocate across all 8 ATC classes — derived from the scenario's service-level target, not an observed warehouse capacity."
            />
            <MetricCard
              label="Improvement vs. Baseline"
              value={formatPercent(result.improvement_pct)}
              helperText="Weighted expected shortage, same total inventory exposure"
              tooltip="Reduction in total volume-weighted expected shortage vs. the naive equal-target baseline policy, for the same total capacity budget."
            />
            <MetricCard
              label="Baseline Weighted Shortage"
              value={formatDecimal(result.allocation_baseline.total_weighted_expected_shortage)}
              helperText="Naive equal-target policy"
            />
            <MetricCard
              label="Optimized Weighted Shortage"
              value={formatDecimal(result.allocation_optimized.total_weighted_expected_shortage)}
              helperText="This scenario's LP allocation"
            />
          </div>

          <Table
            caption="Scenario assumptions used for this optimization run"
            columns={assumptionColumns}
            rows={result.assumptions}
            rowKey={(row) => row.parameter}
            density="compact"
          />
        </>
      )}
    </div>
  );
}
