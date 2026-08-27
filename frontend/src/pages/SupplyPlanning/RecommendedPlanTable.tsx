import { Skeleton } from "../../components/ui/Skeleton/Skeleton";
import { SectionHeader } from "../../components/ui/SectionHeader/SectionHeader";
import { Table, type TableColumn } from "../../components/ui/Table/Table";
import { formatDecimal, formatFraction } from "../../lib/format";
import { ATC_CLASSES } from "../../types/api";
import type { AtcPlanningResult, OptimizationRunResponse } from "../../types/api";
import styles from "./SupplyPlanning.module.css";

export interface RecommendedPlanTableProps {
  /** The last SUCCESSFUL run's result — see index.tsx's `lastSuccess` state. */
  result: OptimizationRunResponse | null;
  isPending: boolean;
}

const columns: TableColumn<AtcPlanningResult>[] = [
  { key: "atc_class", header: "ATC Class", render: (row) => row.atc_class },
  { key: "model", header: "Forecast Model", render: (row) => row.model_used },
  { key: "service_level", header: "Implied Service Level", align: "end", render: (row) => formatFraction(row.service_level, 1) },
  { key: "safety_stock", header: "Safety Stock", align: "end", render: (row) => `${formatDecimal(row.safety_stock)} units` },
  { key: "reorder_point", header: "Reorder Point", align: "end", render: (row) => `${formatDecimal(row.reorder_point)} units` },
  { key: "order_qty", header: "Recommended Order Qty", align: "end", render: (row) => `${formatDecimal(row.recommended_order_quantity)} units` },
  { key: "expected_shortage", header: "Expected Shortage", align: "end", render: (row) => `${formatDecimal(row.expected_shortage)} units` },
];

/**
 * Per-class recommendation — the LP-optimized safety stock/reorder
 * point/order quantity for each ATC class. This is the ONLY place a
 * per-class figure appears: the API does not return a per-class
 * baseline breakdown to diff against (see
 * docs/frontend-supply-planning-optimization-page.md), so there is
 * intentionally no "change" column here — the baseline comparison
 * exists only at the aggregate level, in OptimizationSummary.
 */
export function RecommendedPlanTable({ result, isPending }: RecommendedPlanTableProps) {
  if (isPending && !result) {
    return (
      <div className={styles.sectionStack}>
        <SectionHeader id="plan-heading" eyebrow="Recommendation" title="Recommended Plan" description="Per-class safety stock, reorder point, and order quantity." />
        <Skeleton variant="table" count={8} />
      </div>
    );
  }

  if (!result) return null;

  const rows = ATC_CLASSES.filter((atc) => atc in result.atc_results).map((atc) => result.atc_results[atc]!);

  return (
    <div className={styles.sectionStack}>
      <SectionHeader
        id="plan-heading"
        eyebrow="Recommendation"
        title="Recommended Plan"
        description="Per-class safety stock, reorder point, and order quantity from the optimized allocation."
      />
      <Table
        caption="Recommended per-ATC-class safety stock, reorder point, order quantity, implied service level, and expected shortage"
        columns={columns}
        rows={rows}
        rowKey={(row) => row.atc_class}
        density="compact"
      />
    </div>
  );
}
