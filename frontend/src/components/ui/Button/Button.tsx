import { forwardRef } from "react";
import type { ButtonHTMLAttributes, ReactNode } from "react";
import { Loader2 } from "lucide-react";
import { cx } from "../../../lib/cx";
import styles from "./Button.module.css";

export type ButtonVariant = "primary" | "secondary" | "ghost" | "danger";
export type ButtonSize = "sm" | "md";

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
  loading?: boolean;
  icon?: ReactNode;
  iconPosition?: "start" | "end";
}

/** Icon-only buttons (icon set, no children) MUST pass `aria-label` — a
 * dev-only console warning fires if one is missing, since TypeScript
 * can't cleanly express "required only when there are no children". */
export const Button = forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  {
    variant = "primary",
    size = "md",
    loading = false,
    icon,
    iconPosition = "start",
    disabled,
    children,
    className,
    type = "button",
    "aria-label": ariaLabel,
    ...rest
  },
  ref,
) {
  const isIconOnly = Boolean(icon) && !children;

  if (import.meta.env.DEV && isIconOnly && !ariaLabel && !rest["aria-labelledby"]) {
    console.warn("Button: an icon-only button must have an aria-label (or aria-labelledby).");
  }

  return (
    <button
      ref={ref}
      type={type}
      className={cx(styles.button, styles[variant], styles[size], loading && styles.loading, className)}
      disabled={disabled || loading}
      aria-busy={loading || undefined}
      aria-label={ariaLabel}
      {...rest}
    >
      {loading ? (
        <Loader2 className={styles.spinner} aria-hidden="true" size={size === "sm" ? 14 : 16} />
      ) : (
        icon &&
        iconPosition === "start" && (
          <span className={styles.icon} aria-hidden="true">
            {icon}
          </span>
        )
      )}
      {children}
      {!loading && icon && iconPosition === "end" && (
        <span className={styles.icon} aria-hidden="true">
          {icon}
        </span>
      )}
    </button>
  );
});
