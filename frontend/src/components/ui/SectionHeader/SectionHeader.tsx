import type { ReactNode } from "react";
import styles from "./SectionHeader.module.css";

export interface SectionHeaderProps {
  /** Small label above the title, e.g. a section category. */
  eyebrow?: string;
  title: string;
  description?: string;
  action?: ReactNode;
  /** Heading level, so callers keep the page's heading hierarchy correct. */
  as?: "h1" | "h2" | "h3";
}

/** A consistent heading block for pages and page sections — title plus
 * optional eyebrow, description, and a trailing action (e.g. a
 * DateRange control or export button). */
export function SectionHeader({ eyebrow, title, description, action, as: Heading = "h2" }: SectionHeaderProps) {
  return (
    <div className={styles.wrapper}>
      <div className={styles.text}>
        {eyebrow && <p className={styles.eyebrow}>{eyebrow}</p>}
        <Heading className={styles.title}>{title}</Heading>
        {description && <p className={styles.description}>{description}</p>}
      </div>
      {action && <div className={styles.action}>{action}</div>}
    </div>
  );
}
