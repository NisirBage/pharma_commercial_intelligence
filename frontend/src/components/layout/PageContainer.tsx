import type { ReactNode } from "react";
import styles from "./PageContainer.module.css";

export interface PageContainerProps {
  children: ReactNode;
}

/** Constrains page content to a readable max width with responsive
 * padding and consistent vertical rhythm — every page renders its
 * content inside this, not directly inside <main>. */
export function PageContainer({ children }: PageContainerProps) {
  return <div className={styles.container}>{children}</div>;
}
