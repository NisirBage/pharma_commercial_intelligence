import styles from "./ChartLegend.module.css";

export interface ChartLegendItem {
  label: string;
  color: string;
  /** Marks a series as a range/interval (rendered as a swatch outline
   * rather than a filled dot) — e.g. a forecast confidence interval. */
  variant?: "line" | "area";
}

export interface ChartLegendProps {
  items: ChartLegendItem[];
}

/** The consistent legend every chart in the app uses — a color swatch
 * plus text label per series, never color alone (the label always
 * carries the meaning). Caller supplies the real series list; this
 * renders no example data of its own. */
export function ChartLegend({ items }: ChartLegendProps) {
  if (items.length === 0) return null;

  return (
    <ul className={styles.legend}>
      {items.map((item) => (
        <li key={item.label} className={styles.item}>
          <span
            className={item.variant === "area" ? styles.swatchArea : styles.swatchLine}
            style={{ backgroundColor: item.color }}
            aria-hidden="true"
          />
          <span className={styles.label}>{item.label}</span>
        </li>
      ))}
    </ul>
  );
}
