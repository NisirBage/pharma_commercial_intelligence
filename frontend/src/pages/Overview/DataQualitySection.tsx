import type { UseQueryResult } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { Card } from "../../components/ui/Card/Card";
import { ErrorState } from "../../components/ui/ErrorState/ErrorState";
import { SectionHeader } from "../../components/ui/SectionHeader/SectionHeader";
import { Skeleton } from "../../components/ui/Skeleton/Skeleton";
import { StatusBadge } from "../../components/ui/StatusBadge/StatusBadge";
import { getDataQualityStatus } from "../../lib/domainLabels";
import { formatCount } from "../../lib/format";
import type { DataQualityResponse, Health } from "../../types/api";
import styles from "./Overview.module.css";

export interface DataQualitySectionProps {
  query: UseQueryResult<DataQualityResponse, unknown>;
  healthQuery: UseQueryResult<Health, unknown>;
}

/** Overall status, per-grain reconciliation, and the documented monthly
 * inconsistency warning — which the API returns unconditionally and
 * this section always renders, never hides (M6 Sec. 19 / M7.4 Sec. 7). */
export function DataQualitySection({ query, healthQuery }: DataQualitySectionProps) {
  const { data, isLoading, isError, error, refetch } = query;

  return (
    <section aria-labelledby="data-quality-heading">
      <SectionHeader
        id="data-quality-heading"
        eyebrow="Trust"
        title="Data Quality"
        description="Source reconciliation status for the underlying dataset."
        action={
          <Link to="/data-quality" className={styles.sectionLink}>
            View full report →
          </Link>
        }
      />
      <Card>
        {isLoading ? (
          <Skeleton variant="text" count={4} />
        ) : isError ? (
          <ErrorState title="Couldn't load data-quality status" error={error} onRetry={() => refetch()} />
        ) : !data ? (
          <ErrorState title="No data-quality report available" message="The API returned no data." onRetry={() => refetch()} />
        ) : (
          <div className={styles.dataQualityBody}>
            <div className={styles.dataQualityRow}>
              <span className={styles.dataQualityLabel}>Overall status</span>
              <StatusBadge status={getDataQualityStatus(data.overall_status)} label={data.overall_status.toUpperCase()} />
            </div>
            <ul className={styles.reconciliationList}>
              {data.reconciliation.map((r) => (
                <li key={r.label} className={styles.dataQualityRow}>
                  <span className={styles.dataQualityLabel}>{r.label} reconciliation</span>
                  <div className={styles.dataQualityStatusGroup}>
                    <StatusBadge status={getDataQualityStatus(r.status)} label={r.status.toUpperCase()} />
                    {!r.reconciled && <span className={styles.dataQualityNote}>{r.note}</span>}
                  </div>
                </li>
              ))}
            </ul>
            {data.monthly_inconsistency_warning && (
              <p className={styles.warningNote}>{data.monthly_inconsistency_warning}</p>
            )}
            <p className={styles.mutedNote}>
              {data.file_summaries.length} source file{data.file_summaries.length === 1 ? "" : "s"},{" "}
              {formatCount(data.file_summaries.reduce((sum, f) => sum + f.total_records, 0))} total records.
            </p>
            {healthQuery.data && (
              <div className={styles.dataQualityRow}>
                <span className={styles.dataQualityLabel}>API status</span>
                <StatusBadge
                  status={healthQuery.data.status === "ok" ? "healthy" : "error"}
                  label={healthQuery.data.status}
                />
              </div>
            )}
          </div>
        )}
      </Card>
    </section>
  );
}
