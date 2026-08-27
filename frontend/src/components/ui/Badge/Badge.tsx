import type { ReactNode } from "react";
import { cx } from "../../../lib/cx";
import styles from "./Badge.module.css";

export type BadgeVariant = "neutral" | "info" | "success" | "warning" | "danger";

export interface BadgeProps {
  variant?: BadgeVariant;
  children: ReactNode;
}

export function Badge({ variant = "neutral", children }: BadgeProps) {
  return <span className={cx(styles.badge, styles[variant])}>{children}</span>;
}
