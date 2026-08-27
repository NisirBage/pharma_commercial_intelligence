import { useId } from "react";
import { cx } from "../../lib/cx";
import styles from "./SupplyPlanning.module.css";

export interface NumberFieldProps {
  label: string;
  value: string;
  onChange: (value: string) => void;
  min: number;
  max: number;
  step?: number;
  unit?: string;
  helperText?: string;
  error?: string;
  placeholder?: string;
}

/**
 * A bounded numeric override input — for the two OptimizationRunRequest
 * fields (service_level, lead_time_days) the existing Select/DateRange
 * components don't cover (a Select handles enums, DateRange handles
 * dates; nothing in components/ui/ handles "a bounded decimal with a
 * unit"). Page-local rather than promoted to components/ui/ since no
 * second page needs it yet — mirrors Select's accessible label/helper/
 * error wiring exactly, so it reads as the same design system.
 */
export function NumberField({ label, value, onChange, min, max, step = 1, unit, helperText, error, placeholder }: NumberFieldProps) {
  const id = useId();
  const helperId = helperText ? `${id}-helper` : undefined;
  const errorId = error ? `${id}-error` : undefined;
  const describedBy = cx(helperId, errorId) || undefined;

  return (
    <div className={styles.field}>
      <label htmlFor={id} className={styles.fieldLabel}>
        {label}
        {unit && <span className={styles.fieldUnit}> ({unit})</span>}
      </label>
      <input
        id={id}
        type="number"
        className={cx(styles.numberInput, error && styles.numberInputError)}
        value={value}
        min={min}
        max={max}
        step={step}
        placeholder={placeholder}
        onChange={(e) => onChange(e.target.value)}
        aria-describedby={describedBy}
        aria-invalid={error ? true : undefined}
      />
      {helperText && !error && (
        <p id={helperId} className={styles.fieldHelper}>
          {helperText}
        </p>
      )}
      {error && (
        <p id={errorId} className={styles.fieldError} role="alert">
          {error}
        </p>
      )}
    </div>
  );
}
