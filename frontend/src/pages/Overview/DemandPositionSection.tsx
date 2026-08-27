import type { UseQueryResult } from "@tanstack/react-query";
import { Card } from "../../components/ui/Card/Card";
import { ErrorState } from "../../components/ui/ErrorState/ErrorState";
import { SectionHeader } from "../../components/ui/SectionHeader/SectionHeader";
import { Skeleton } from "../../components/ui/Skeleton/Skeleton";
import { formatDateRange, formatPercent } from "../../lib/format";
import type { AtcPerformanceResponse, KpiSummary } from "../../types/api";
import styles from "./Overview.module.css";

export interface DemandPositionSectionProps {
  kpiQuery: UseQueryResult<KpiSummary, unknown>;
  atcQuery: UseQueryResult<AtcPerformanceResponse, unknown>;
}

/** An executive read on the aggregate position: dominant class/share/
 * period from the KPI summary, plus a plain tally of per-class trend
 * classifications from ATC analytics. Deliberately does NOT assert an
 * "aggregate trend" — no endpoint computes one (only per-class trends
 * exist), and inventing a pooled-trend verdict client-side would be
 * exactly the kind of frontend-side statistic M7.4 prohibits. */
export function DemandPositionSection({ kpiQuery, atcQuery }: DemandPositionSectionProps) {
  return (
    <section aria-labelledby="demand-position-heading">
      <SectionHeader
        id="demand-position-heading"
        eyebrow="Interpretation"
        title="Demand Position"
        description="A concise read on the aggregate commercial position."
      />
      <Card>
        {kpiQuery.isLoading ? (
          <Skeleton variant="text" count={2} />
        ) : kpiQuery.isError ? (
          <ErrorState title="Couldn't load the demand position" error={kpiQuery.error} onRetry={() => kpiQuery.refetch()} />
        ) : (
          <div className={styles.positionBody}>
            <p>
              {kpiQuery.data?.dominant_atc_class ? (
                <>
                  <strong>{kpiQuery.data.dominant_atc_class}</strong> is the dominant ATC class, representing{" "}
                  <strong>{formatPercent(kpiQuery.data.dominant_atc_share_pct)}</strong> of total observed demand
                  {kpiQuery.data.period.start && kpiQuery.data.period.end
                    ? ` over ${formatDateRange(kpiQuery.data.period.start, kpiQuery.data.period.end)}`
                    : ""}
                  .
                </>
              ) : (
                "No dominant ATC class is available from the API."
              )}
            </p>
            <TrendSignalSummary atcQuery={atcQuery} />
          </div>
        )}
      </Card>
    </section>
  );
}

function TrendSignalSummary({ atcQuery }: { atcQuery: UseQueryResult<AtcPerformanceResponse, unknown> }) {
  if (atcQuery.isLoading) return <Skeleton variant="text" count={1} />;
  if (atcQuery.isError) {
    return <p className={styles.mutedNote}>Trend detail is unavailable right now — see Commercial Signals below.</p>;
  }
  const classes = atcQuery.data?.classes ?? [];
  if (classes.length === 0) return null;

  const growing = classes.filter((c) => c.trend_classification === "growing").length;
  const declining = classes.filter((c) => c.trend_classification === "declining").length;
  const stable = classes.length - growing - declining;

  return (
    <p className={styles.mutedNote}>
      Across {classes.length} observed ATC classes: {growing} statistically significant growing, {declining}{" "}
      statistically significant declining, {stable} with no significant trend detected.
    </p>
  );
}
