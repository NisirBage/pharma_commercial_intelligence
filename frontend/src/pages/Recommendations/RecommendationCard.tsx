import { Badge } from "../../components/ui/Badge/Badge";
import { Card } from "../../components/ui/Card/Card";
import { getRecommendationConfidenceDisplay } from "../../lib/domainLabels";
import type { RecommendationItem } from "../../types/api";
import styles from "./Recommendations.module.css";

export interface RecommendationCardProps {
  item: RecommendationItem;
}

/**
 * One ATC class's recommendation — every field is the API's own text,
 * shown verbatim (never rewritten, never re-derived). Evidence and
 * limitations are always visible (both directly support "why does
 * this exist" and, for limitations, are sometimes class-specific
 * caveats — never appropriate to hide). Assumptions are the same two
 * standard scenario-wide sentences on almost every card, so they sit
 * behind a native `<details>` (keyboard-accessible with no extra ARIA
 * needed) to keep 8 cards scannable without losing the information.
 */
export function RecommendationCard({ item }: RecommendationCardProps) {
  const confidence = getRecommendationConfidenceDisplay(item.confidence);

  return (
    <Card>
      <div className={styles.cardHeader}>
        <span className={styles.atcClass}>{item.atc_class}</span>
        <Badge variant={confidence.variant}>{confidence.label}</Badge>
      </div>

      <p className={styles.recommendationText}>{item.recommendation}</p>

      {item.expected_effect && (
        <div className={styles.subBlock}>
          <p className={styles.subBlockLabel}>Expected effect</p>
          <p className={styles.expectedEffect}>{item.expected_effect}</p>
        </div>
      )}

      {item.evidence.length > 0 && (
        <div className={styles.subBlock}>
          <p className={styles.subBlockLabel}>Evidence</p>
          <ul className={styles.bulletList}>
            {item.evidence.map((line) => (
              <li key={line}>{line}</li>
            ))}
          </ul>
        </div>
      )}

      {item.limitations.length > 0 && (
        <div className={styles.subBlock}>
          <p className={styles.subBlockLabel}>Limitations</p>
          <ul className={`${styles.bulletList} ${styles.limitationsList}`}>
            {item.limitations.map((line) => (
              <li key={line}>{line}</li>
            ))}
          </ul>
        </div>
      )}

      {item.assumptions.length > 0 && (
        <details className={styles.assumptionsDetails}>
          <summary className={styles.assumptionsSummary}>Assumptions</summary>
          <ul className={`${styles.bulletList} ${styles.assumptionsList}`}>
            {item.assumptions.map((line) => (
              <li key={line}>{line}</li>
            ))}
          </ul>
        </details>
      )}
    </Card>
  );
}
