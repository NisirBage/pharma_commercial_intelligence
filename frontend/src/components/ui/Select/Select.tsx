import type { SelectHTMLAttributes } from "react";
import { useId } from "react";
import { cx } from "../../../lib/cx";
import styles from "./Select.module.css";

export interface SelectOption {
  value: string;
  label: string;
}

export interface SelectProps extends Omit<SelectHTMLAttributes<HTMLSelectElement>, "id"> {
  label: string;
  options: SelectOption[];
  helperText?: string;
  error?: string;
  hideLabel?: boolean;
}

/** A native <select> — no custom listbox implementation, per M7.3
 * Sec. 11 ("native preferred unless inspection shows a real
 * requirement"). Nothing in this app needs multi-select, search, or
 * custom option rendering. */
export function Select({ label, options, helperText, error, hideLabel = false, className, ...rest }: SelectProps) {
  const id = useId();
  const helperId = helperText ? `${id}-helper` : undefined;
  const errorId = error ? `${id}-error` : undefined;
  const describedBy = cx(helperId, errorId) || undefined;

  return (
    <div className={styles.field}>
      <label htmlFor={id} className={cx(styles.label, hideLabel && "visually-hidden")}>
        {label}
      </label>
      <select
        id={id}
        className={cx(styles.select, error && styles.hasError, className)}
        aria-invalid={error ? true : undefined}
        aria-describedby={describedBy}
        {...rest}
      >
        {options.map((opt) => (
          <option key={opt.value} value={opt.value}>
            {opt.label}
          </option>
        ))}
      </select>
      {helperText && !error && (
        <p id={helperId} className={styles.helperText}>
          {helperText}
        </p>
      )}
      {error && (
        <p id={errorId} className={styles.errorText} role="alert">
          {error}
        </p>
      )}
    </div>
  );
}
