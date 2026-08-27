import { Card } from "../../components/ui/Card/Card";
import { EmptyState } from "../../components/ui/EmptyState/EmptyState";
import { ErrorState } from "../../components/ui/ErrorState/ErrorState";
import { SectionHeader } from "../../components/ui/SectionHeader/SectionHeader";
import { Skeleton } from "../../components/ui/Skeleton/Skeleton";
import { StatusBadge } from "../../components/ui/StatusBadge/StatusBadge";
import { Table, type TableColumn } from "../../components/ui/Table/Table";
import { useDataQuality } from "../../hooks/useDataQuality";
import { useHealth } from "../../hooks/useHealth";
import { getDataQualityStatus } from "../../lib/domainLabels";
import { formatCount } from "../../lib/format";
import type { FileSummary } from "../../types/api";
import styles from "./DataQuality.module.css";

const fileColumns: TableColumn<FileSummary>[] = [
  { key: "file_name", header: "Source File", render: (row) => row.file_name },
  { key: "total", header: "Total Records", align: "end", render: (row) => formatCount(row.total_records) },
  { key: "valid", header: "Valid Records", align: "end", render: (row) => formatCount(row.valid_records) },
  { key: "rejected", header: "Rejected Records", align: "end", render: (row) => formatCount(row.rejected_records) },
];

/**
 * Data Quality — the full source reconciliation and file-level ingestion
 * report. GET /api/v1/data-quality is the same endpoint and the same
 * `useDataQuality()` hook the Overview page's summary card already
 * reads (M7.4) — TanStack Query's cache means arriving here right after
 * Overview is typically an instant hit, not a second request. This page
 * shows everything the response carries that the Overview summary
 * deliberately keeps compact: the dataset's own source id, every
 * reconciliation check's note (not just the ones that failed), and the
 * per-file total/valid/rejected record counts, which appear nowhere
 * else in the app. The documented monthly reconciliation warning is
 * always rendered, exactly like the Overview summary — this endpoint
 * reports it unconditionally and neither surface hides it (M6 Sec. 19).
 */
export function DataQualityPage() {
  const { data, isLoading, isError, error, refetch } = useDataQuality();
  const healthQuery = useHealth();

  return (
    <div className={styles.page}>
      <SectionHeader
        as="h1"
        title="Data Quality"
        description="Source reconciliation status and per-file ingestion counts for the underlying dataset."
      />

      {isError ? (
        <ErrorState title="Couldn't load the data-quality report" error={error} onRetry={() => refetch()} />
      ) : isLoading ? (
        <div className={styles.sectionStack}>
          <Card>
            <Skeleton variant="text" count={2} />
          </Card>
          <Skeleton variant="table" count={5} />
        </div>
      ) : !data ? (
        <EmptyState title="No data-quality report available" description="The API returned no data." />
      ) : (
        <div className={styles.sectionStack}>
          <section aria-labelledby="overall-status-heading">
            <SectionHeader id="overall-status-heading" eyebrow="Status" title="Overall Status" as="h2" />
            <Card>
              <div className={styles.overallRow}>
                <StatusBadge status={getDataQualityStatus(data.overall_status)} label={data.overall_status.toUpperCase()} />
                <span className={styles.datasetId}>Source dataset: {data.kaggle_dataset_id}</span>
              </div>
              {healthQuery.data && (
                <p className={styles.mutedNote}>
                  API status: {healthQuery.data.status} (v{healthQuery.data.version}, {healthQuery.data.environment})
                </p>
              )}
            </Card>
          </section>

          <section aria-labelledby="reconciliation-heading">
            <SectionHeader
              id="reconciliation-heading"
              eyebrow="Reconciliation"
              title="Cross-Granularity Reconciliation"
              description="Whether the daily, weekly, and monthly aggregations of this dataset agree with each other."
              as="h2"
            />
            <Card>
              {data.reconciliation.length === 0 ? (
                <EmptyState title="No reconciliation checks available" description="The API returned no reconciliation results." />
              ) : (
                <ul className={styles.reconciliationList}>
                  {data.reconciliation.map((r) => (
                    <li key={r.label} className={styles.reconciliationItem}>
                      <div className={styles.reconciliationHeader}>
                        <span className={styles.reconciliationLabel}>{r.label} reconciliation</span>
                        <StatusBadge status={getDataQualityStatus(r.status)} label={r.status.toUpperCase()} />
                      </div>
                      {r.note && <p className={styles.reconciliationNote}>{r.note}</p>}
                    </li>
                  ))}
                </ul>
              )}
              {data.monthly_inconsistency_warning && <p className={styles.warningNote}>{data.monthly_inconsistency_warning}</p>}
            </Card>
          </section>

          <section aria-labelledby="file-summaries-heading">
            <SectionHeader
              id="file-summaries-heading"
              eyebrow="Ingestion"
              title="Source Files"
              description="Record counts for every source file ingested into this dataset."
              as="h2"
            />
            {data.file_summaries.length === 0 ? (
              <EmptyState title="No source files available" description="The API returned no file-level summaries." />
            ) : (
              <Table
                caption="Per-file record counts: total, valid, and rejected"
                columns={fileColumns}
                rows={data.file_summaries}
                rowKey={(row) => row.file_name}
                density="compact"
              />
            )}
          </section>
        </div>
      )}
    </div>
  );
}
