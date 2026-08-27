import type { ReactNode } from "react";
import { useId, useState } from "react";
import styles from "./Tooltip.module.css";

export interface TooltipProps {
  /** The term or control the tooltip explains — e.g. a KPI label or a
   * statistical/forecasting term. Must be focusable (button, or an
   * element with tabIndex) so keyboard users can reach the tooltip. */
  children: ReactNode;
  /** The explanatory content. Never put information here that is
   * required to use the page — tooltips supplement, they don't hide. */
  content: string;
  placement?: "top" | "bottom";
}

/** A lightweight, dependency-free tooltip shown on hover OR focus, so
 * keyboard and screen-reader users get the same information as mouse
 * users. Intended for KPI definitions and forecasting/optimization
 * terminology — never for critical information with no other access
 * path. */
export function Tooltip({ children, content, placement = "top" }: TooltipProps) {
  const [visible, setVisible] = useState(false);
  const id = useId();

  const show = () => setVisible(true);
  const hide = () => setVisible(false);

  return (
    <span
      className={styles.wrapper}
      onMouseEnter={show}
      onMouseLeave={hide}
      onFocus={show}
      onBlur={hide}
    >
      <span aria-describedby={id} className={styles.trigger}>
        {children}
      </span>
      <span role="tooltip" id={id} className={`${styles.bubble} ${styles[placement]} ${visible ? styles.visible : ""}`}>
        {content}
      </span>
    </span>
  );
}
