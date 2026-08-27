import type { UseQueryResult } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { EmptyState } from "../../components/ui/EmptyState/EmptyState";
import { ErrorState } from "../../components/ui/ErrorState/ErrorState";
import { SectionHeader } from "../../components/ui/SectionHeader/SectionHeader";
import { Skeleton } from "../../components/ui/Skeleton/Skeleton";
import { Table, type TableColumn } from "../../components/ui/Table/Table";
import { formatFraction } from "../../lib/format";
import type { ScenarioInfo, ScenariosResponse } from "../../types/api";
import styles from "./Overview.module.css";

export interface SupplyPlanningPreviewSectionProps {
  query: UseQueryResult<ScenariosResponse, unknown>;
}

const columns: TableColumn<ScenarioInfo>[] = [
  { key: "name", header: "Scenario", render: (row) => `${row.name[0]!.toUpperCase()}${row.name.slice(1)}` },
  { key: "service_level", header: "Service Level", align: "end", render: (row) => formatFraction(row.service_level_target) },
  { key: "lead_time", header: "Lead Time", align: "end", render: (row) => `${row.lead_time_days}d` },
  { key: "review_period", header: "Review Period", align: "end", render: (row) => `${row.review_period_days}d` },
];

/** "Where are the major planning/supply implications?" — GET
 * /api/v1/optimization/scenarios only describes the 3 available
 * scenarios (their targets, not a result); the optimizer itself is a
 * POST (`useOptimizationRun`, a mutation) that must never fire on
 * page load (M7.7 Sec. 21) — so there is no legitimate GET source for
 * an "optimized allocation" or "improvement %" figure to preview here.
 * This section is deliberately limited to the real scenario
 * definitions, with an explicit note that running one is what produces
 * an allocation result, rather than fabricating one. */
export function SupplyPlanningPreviewSection({ query }: SupplyPlanningPreviewSectionProps) {
  const { data, isLoading, isError, error, refetch } = query;

  return (
    <section aria-labelledby="planning-preview-heading">
      <SectionHeader
        id="planning-preview-heading"
        eyebrow="Planning"
        title="Supply Planning & Optimization"
        description="Scenario-based safety-stock planning across ATC classes."
        action={
          <Link to="/planning" className={styles.sectionLink}>
            Open Supply Planning →
          </Link>
        }
      />
      {isLoading ? (
        <Skeleton variant="table" count={3} />
      ) : isError ? (
        <ErrorState title="Couldn't load planning scenarios" error={error} onRetry={() => refetch()} />
      ) : !data || data.scenarios.length === 0 ? (
        <EmptyState title="No planning scenarios available" description="The API returned no scenario definitions." />
      ) : (
        <>
          <Table
            caption="Available planning scenarios: service level target, lead time, and review period"
            columns={columns}
            rows={data.scenarios}
            rowKey={(row) => row.name}
            density="compact"
          />
          <p className={styles.mutedNote}>
            These are scenario definitions, not a result — an optimized allocation, capacity budget, and improvement figure
            only exist after running a scenario on the Supply Planning page.
          </p>
        </>
      )}
    </section>
  );
}
