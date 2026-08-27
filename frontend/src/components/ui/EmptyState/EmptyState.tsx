import type { ReactNode } from "react";
import { Inbox } from "lucide-react";
import styles from "./EmptyState.module.css";

export interface EmptyStateProps {
  icon?: ReactNode;
  title: string;
  description?: string;
  action?: ReactNode;
}

/** Shown when a query succeeds but returns no data to display — e.g. an
 * ATC class with no rows for the selected date range. Not for errors;
 * see ErrorState for that. */
export function EmptyState({ icon, title, description, action }: EmptyStateProps) {
  return (
    <div className={styles.wrapper}>
      <div className={styles.icon} aria-hidden="true">
        {icon ?? <Inbox size={28} strokeWidth={1.5} />}
      </div>
      <p className={styles.title}>{title}</p>
      {description && <p className={styles.description}>{description}</p>}
      {action && <div className={styles.action}>{action}</div>}
    </div>
  );
}
