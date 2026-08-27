import styles from "./ChartTooltip.module.css";

export interface ChartTooltipEntry {
  name?: string;
  value?: string | number;
  color?: string;
}

export interface ChartTooltipProps {
  /** Matches Recharts' `<Tooltip active>` prop — false/undefined while
   * the pointer isn't over a data point. */
  active?: boolean;
  /** Matches Recharts' `<Tooltip payload>` prop shape closely enough to
   * pass straight through from `content={(props) => <ChartTooltip {...props} />}`. */
  payload?: ChartTooltipEntry[];
  label?: string | number;
  /** Overrides how the label (e.g. a date) is displayed. */
  formatLabel?: (label: string | number) => string;
}

/** The one tooltip Recharts consumers in M7.5+ should render via
 * `<Tooltip content={(props) => <ChartTooltip {...props} />} />`, so
 * every chart's tooltip looks the same. Purely presentational — it
 * renders whatever payload Recharts hands it at runtime, never
 * fabricated data. */
export function ChartTooltip({ active, payload, label, formatLabel }: ChartTooltipProps) {
  if (!active || !payload || payload.length === 0) return null;

  return (
    // Deliberately no ARIA live region: this fires on every pointer
    // move, and announcing that would spam screen reader users. Charts
    // need a non-hover-dependent accessible alternative (e.g. a data
    // table) — that's a M7.5/M7.6 concern when a real chart exists.
    <div className={styles.tooltip}>
      {label !== undefined && (
        <p className={styles.label}>{formatLabel ? formatLabel(label) : label}</p>
      )}
      <ul className={styles.list}>
        {payload.map((entry, index) => (
          <li key={`${entry.name ?? "series"}-${index}`} className={styles.row}>
            {entry.color && (
              <span className={styles.swatch} style={{ backgroundColor: entry.color }} aria-hidden="true" />
            )}
            <span className={styles.name}>{entry.name}</span>
            <span className={styles.value}>{entry.value}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
