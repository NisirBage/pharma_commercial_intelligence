import type { ReactNode } from "react";
import { Card } from "../ui/Card/Card";
import { DEFAULT_CHART_HEIGHT } from "./chartTheme";
import styles from "./ChartCard.module.css";

export interface ChartCardProps {
  title: string;
  subtitle?: string;
  /** e.g. a DateRange or Select controlling what the chart shows. */
  action?: ReactNode;
  /** Height (px) of the chart area. The child chart should fill it via
   * Recharts' `<ResponsiveContainer width="100%" height="100%">` — this
   * is the one place that convention is decided, so every chart page
   * agrees on it. */
  height?: number;
  /** A single chart element (M7.5+), or a Skeleton/EmptyState/ErrorState
   * while the chart's data is loading, empty, or unavailable. ChartCard
   * itself never renders example chart data. */
  children: ReactNode;
  /** Typically a ChartLegend. */
  footer?: ReactNode;
}

/** The consistent container every chart in the app renders inside:
 * title + optional subtitle/action header, a fixed-height responsive
 * chart area, and an optional legend footer. No chart or dataset is
 * implemented here — M7.5/M7.6 supply the actual chart as `children`. */
export function ChartCard({ title, subtitle, action, height = DEFAULT_CHART_HEIGHT, children, footer }: ChartCardProps) {
  return (
    <Card>
      <div className={styles.header}>
        <div className={styles.headerText}>
          <h3 className={styles.title}>{title}</h3>
          {subtitle && <p className={styles.subtitle}>{subtitle}</p>}
        </div>
        {action && <div className={styles.action}>{action}</div>}
      </div>
      <div className={styles.chartArea} style={{ height }}>
        {children}
      </div>
      {footer && <div className={styles.footer}>{footer}</div>}
    </Card>
  );
}
