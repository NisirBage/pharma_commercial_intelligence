import { cx } from "../../../lib/cx";
import styles from "./Skeleton.module.css";

export interface SkeletonProps {
  variant?: "text" | "metric" | "card" | "table" | "chart";
  /** Number of skeleton rows/lines to render (only used by "text" and "table"). */
  count?: number;
  className?: string;
}

/** A loading placeholder shown while a query is pending. Never render
 * fabricated numbers or labels here — only neutral shape placeholders. */
export function Skeleton({ variant = "text", count = 3, className }: SkeletonProps) {
  if (variant === "text") {
    return (
      <div className={cx(styles.textGroup, className)} role="status" aria-label="Loading">
        {Array.from({ length: count }).map((_, i) => (
          <div key={i} className={styles.textLine} style={{ width: i === count - 1 ? "60%" : "100%" }} />
        ))}
      </div>
    );
  }

  if (variant === "metric") {
    return (
      <div className={cx(styles.metric, className)} role="status" aria-label="Loading">
        <div className={styles.metricLabel} />
        <div className={styles.metricValue} />
      </div>
    );
  }

  if (variant === "card") {
    return (
      <div className={cx(styles.card, className)} role="status" aria-label="Loading">
        <div className={styles.cardHeader} />
        <div className={styles.textLine} style={{ width: "90%" }} />
        <div className={styles.textLine} style={{ width: "70%" }} />
      </div>
    );
  }

  if (variant === "table") {
    return (
      <div className={cx(styles.tableGroup, className)} role="status" aria-label="Loading">
        {Array.from({ length: count }).map((_, i) => (
          <div key={i} className={styles.tableRow} />
        ))}
      </div>
    );
  }

  return <div className={cx(styles.chart, className)} role="status" aria-label="Loading" />;
}
