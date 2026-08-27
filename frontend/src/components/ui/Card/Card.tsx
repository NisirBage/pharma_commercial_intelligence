import type { ReactNode } from "react";
import { cx } from "../../../lib/cx";
import styles from "./Card.module.css";

export type CardVariant = "default" | "bordered" | "elevated";

export interface CardProps {
  title?: ReactNode;
  subtitle?: ReactNode;
  headerAction?: ReactNode;
  footer?: ReactNode;
  variant?: CardVariant;
  children?: ReactNode;
  className?: string;
}

export function Card({ title, subtitle, headerAction, footer, variant = "default", children, className }: CardProps) {
  const hasHeader = Boolean(title || subtitle || headerAction);
  return (
    <div className={cx(styles.card, styles[variant], className)}>
      {hasHeader && (
        <div className={styles.header}>
          <div className={styles.headerText}>
            {title && <h3 className={styles.title}>{title}</h3>}
            {subtitle && <p className={styles.subtitle}>{subtitle}</p>}
          </div>
          {headerAction && <div className={styles.headerAction}>{headerAction}</div>}
        </div>
      )}
      {children && <div className={styles.content}>{children}</div>}
      {footer && <div className={styles.footer}>{footer}</div>}
    </div>
  );
}
