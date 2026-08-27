import { Menu } from "lucide-react";
import { useLocation, useParams } from "react-router-dom";
import { matchNavItem } from "./navigation";
import styles from "./Topbar.module.css";

export interface TopbarProps {
  onMenuClick: () => void;
}

/**
 * Derives the current page title (and, for :atcClass routes, a
 * breadcrumb suffix) from the route itself — never a fabricated
 * logged-in-user/avatar/notification area (M7.3 Sec. 20).
 */
export function Topbar({ onMenuClick }: TopbarProps) {
  const location = useLocation();
  const params = useParams<{ atcClass?: string }>();
  const navItem = matchNavItem(location.pathname);
  const title = navItem?.label ?? "Not Found";
  const environment = import.meta.env.MODE;

  return (
    <header className={styles.topbar}>
      <button type="button" className={styles.menuButton} onClick={onMenuClick} aria-label="Open navigation">
        <Menu size={20} aria-hidden="true" />
      </button>
      <div className={styles.titleGroup}>
        <span className={styles.title}>{title}</span>
        {params.atcClass && (
          <>
            <span className={styles.breadcrumbSeparator} aria-hidden="true">
              /
            </span>
            <span className={styles.breadcrumb}>{params.atcClass}</span>
          </>
        )}
      </div>
      <span className={styles.environment} title={`Running in ${environment} mode`}>
        {environment}
      </span>
    </header>
  );
}
