import type { UseQueryResult } from "@tanstack/react-query";
import { Activity, TrendingDown, TrendingUp } from "lucide-react";
import { Link } from "react-router-dom";
import { Badge } from "../../components/ui/Badge/Badge";
import { Card } from "../../components/ui/Card/Card";
import { EmptyState } from "../../components/ui/EmptyState/EmptyState";
import { ErrorState } from "../../components/ui/ErrorState/ErrorState";
import { SectionHeader } from "../../components/ui/SectionHeader/SectionHeader";
import { Skeleton } from "../../components/ui/Skeleton/Skeleton";
import { getTrendDisplay } from "../../lib/domainLabels";
import { formatCV, formatPValue, formatSlope } from "../../lib/format";
import type { AtcPerformance, AtcPerformanceResponse } from "../../types/api";
import styles from "./Overview.module.css";

export interface CommercialSignalsSectionProps {
  query: UseQueryResult<AtcPerformanceResponse, unknown>;
}

/** Statistically significant (p < 0.05) growth/decline trends and the
 * highest-volatility class, straight from the ATC analytics response.
 * "Significant" here means exactly what app/analytics/trends.py tested
 * — never a subjective read of a chart. Growing/declining classes are
 * distinguished from the interpretation of them (see domainLabels.ts's
 * comment on why they aren't colored success/danger). */
export function CommercialSignalsSection({ query }: CommercialSignalsSectionProps) {
  const { data, isLoading, isError, error, refetch } = query;

  return (
    <section aria-labelledby="signals-heading">
      <SectionHeader
        id="signals-heading"
        eyebrow="Signals"
        title="Commercial Signals"
        description="Statistically significant trend and volatility findings, per ATC class."
      />
      {isLoading ? (
        <Card>
          <Skeleton variant="text" count={4} />
        </Card>
      ) : isError ? (
        <ErrorState title="Couldn't load commercial signals" error={error} onRetry={() => refetch()} />
      ) : !data || data.classes.length === 0 ? (
        <EmptyState title="No ATC class data available" description="The API returned no ATC class performance records." />
      ) : (
        <SignalList classes={data.classes} />
      )}
    </section>
  );
}

function SignalList({ classes }: { classes: AtcPerformance[] }) {
  const significant = classes.filter((c) => c.trend_classification === "growing" || c.trend_classification === "declining");
  const withVolatility = classes.filter((c): c is AtcPerformance & { volatility_cv: number } => c.volatility_cv != null);
  const mostVolatile =
    withVolatility.length > 0 ? withVolatility.reduce((a, b) => (b.volatility_cv > a.volatility_cv ? b : a)) : null;

  if (significant.length === 0 && !mostVolatile) {
    return (
      <EmptyState
        title="No significant signals detected"
        description="No ATC class shows a statistically significant (p < 0.05) growth or decline trend, and volatility data is unavailable."
      />
    );
  }

  return (
    <div className={styles.signalGrid}>
      {significant.length === 0 && (
        <Card>
          <p>No ATC class shows a statistically significant (p &lt; 0.05) growth or decline trend.</p>
        </Card>
      )}
      {significant.map((c) => {
        const trend = getTrendDisplay(c.trend_classification);
        const Icon = c.trend_classification === "growing" ? TrendingUp : TrendingDown;
        return (
          <Card key={c.atc_class}>
            <div className={styles.signalHeader}>
              <span className={styles.signalClass}>
                <Icon size={16} aria-hidden="true" />
                {c.atc_class}
              </span>
              <Badge variant={trend.variant}>{trend.label}</Badge>
            </div>
            <p className={styles.signalDetail}>
              Slope {formatSlope(c.trend_slope)} ({formatPValue(c.trend_p_value)})
            </p>
            <Link to={`/forecast/${c.atc_class}`} className={styles.signalLink}>
              View forecast for {c.atc_class} →
            </Link>
          </Card>
        );
      })}
      {mostVolatile && (
        <Card>
          <div className={styles.signalHeader}>
            <span className={styles.signalClass}>
              <Activity size={16} aria-hidden="true" />
              {mostVolatile.atc_class}
            </span>
            <Badge variant="neutral">Highest variability</Badge>
          </div>
          <p className={styles.signalDetail}>
            Coefficient of variation {formatCV(mostVolatile.volatility_cv)} — the highest among observed ATC classes.
          </p>
          <Link to="/demand?tab=atc" className={styles.signalLink}>
            Investigate {mostVolatile.atc_class} →
          </Link>
        </Card>
      )}
    </div>
  );
}
