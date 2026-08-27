import type { UseQueryResult } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { Badge } from "../../components/ui/Badge/Badge";
import { Card } from "../../components/ui/Card/Card";
import { EmptyState } from "../../components/ui/EmptyState/EmptyState";
import { ErrorState } from "../../components/ui/ErrorState/ErrorState";
import { MetricCard } from "../../components/ui/MetricCard/MetricCard";
import { SectionHeader } from "../../components/ui/SectionHeader/SectionHeader";
import { Skeleton } from "../../components/ui/Skeleton/Skeleton";
import { getRecommendationConfidenceDisplay } from "../../lib/domainLabels";
import type { RecommendationsResponse } from "../../types/api";
import styles from "./Overview.module.css";

export interface RecommendationsPreviewSectionProps {
  query: UseQueryResult<RecommendationsResponse, unknown>;
}

/** "What recommendations require attention?" — the same default
 * (`balanced`-scenario) response the Recommendations page itself reads
 * first, via the identical query key. The total and low-confidence
 * tallies are plain counts of the already-categorical `confidence`
 * field (the same kind of frontend-derived aggregate the Recommendations
 * page's own KPI row computes — see
 * docs/frontend-recommendations-intelligence-page.md), not a new
 * statistic. The single preview card highlights the first low-confidence
 * recommendation (the one most worth scrutinizing) when one exists,
 * falling back to the first recommendation in the API's own order
 * otherwise — never re-sorted. */
export function RecommendationsPreviewSection({ query }: RecommendationsPreviewSectionProps) {
  const { data, isLoading, isError, error, refetch } = query;
  const recommendations = data?.recommendations ?? [];
  const lowCount = recommendations.filter((r) => r.confidence === "low").length;
  const featured = recommendations.find((r) => r.confidence === "low") ?? recommendations[0];

  return (
    <section aria-labelledby="recommendations-preview-heading">
      <SectionHeader
        id="recommendations-preview-heading"
        eyebrow="Recommendations"
        title="Recommendations Intelligence"
        description="Explainable, per-ATC-class planning guidance."
        action={
          <Link to="/recommendations" className={styles.sectionLink}>
            View all recommendations →
          </Link>
        }
      />
      {isLoading ? (
        <div className={styles.sectionStack}>
          <Skeleton variant="text" count={2} />
          <Skeleton variant="card" />
        </div>
      ) : isError ? (
        <ErrorState title="Couldn't load recommendations" error={error} onRetry={() => refetch()} />
      ) : recommendations.length === 0 ? (
        <EmptyState title="No recommendations available" description="The API returned no recommendations for the current scenario." />
      ) : (
        <div className={styles.sectionStack}>
          <div className={styles.previewGrid}>
            <MetricCard label="Total Recommendations" value={String(recommendations.length)} helperText={`Scenario: ${data?.scenario}`} />
            <MetricCard label="Low Confidence" value={String(lowCount)} helperText="Recommendations to scrutinize most" />
          </div>
          {featured && (
            <Card>
              <div className={styles.signalHeader}>
                <span className={styles.signalClass}>{featured.atc_class}</span>
                <Badge variant={getRecommendationConfidenceDisplay(featured.confidence).variant}>
                  {getRecommendationConfidenceDisplay(featured.confidence).label}
                </Badge>
              </div>
              <p className={styles.signalDetail}>{featured.recommendation}</p>
            </Card>
          )}
        </div>
      )}
    </section>
  );
}
