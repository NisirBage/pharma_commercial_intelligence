import { useId } from "react";
import styles from "./DateRange.module.css";

export interface DateRangeProps {
  startLabel?: string;
  endLabel?: string;
  /** ISO date strings (YYYY-MM-DD), matching the format every M6 date
   * query parameter expects — see backend/app/services/validation.py. */
  startValue: string;
  endValue: string;
  onStartChange: (value: string) => void;
  onEndChange: (value: string) => void;
  min?: string;
  max?: string;
  disabled?: boolean;
  error?: string;
}

/** A pair of native date inputs — no date-picker library, per M7.3
 * Sec. 12. Cross-constrains start <= end via each input's own min/max. */
export function DateRange({
  startLabel = "Start date",
  endLabel = "End date",
  startValue,
  endValue,
  onStartChange,
  onEndChange,
  min,
  max,
  disabled = false,
  error,
}: DateRangeProps) {
  const startId = useId();
  const endId = useId();
  const errorId = error ? `${startId}-error` : undefined;

  return (
    <div className={styles.wrapper}>
      <div className={styles.field}>
        <label htmlFor={startId} className={styles.label}>
          {startLabel}
        </label>
        <input
          id={startId}
          type="date"
          className={styles.input}
          value={startValue}
          min={min}
          max={endValue || max}
          disabled={disabled}
          onChange={(event) => onStartChange(event.target.value)}
          aria-describedby={errorId}
          aria-invalid={error ? true : undefined}
        />
      </div>
      <span className={styles.separator} aria-hidden="true">
        &ndash;
      </span>
      <div className={styles.field}>
        <label htmlFor={endId} className={styles.label}>
          {endLabel}
        </label>
        <input
          id={endId}
          type="date"
          className={styles.input}
          value={endValue}
          min={startValue || min}
          max={max}
          disabled={disabled}
          onChange={(event) => onEndChange(event.target.value)}
          aria-describedby={errorId}
          aria-invalid={error ? true : undefined}
        />
      </div>
      {error && (
        <p id={errorId} className={styles.errorText} role="alert">
          {error}
        </p>
      )}
    </div>
  );
}
