import { NavLink } from "react-router-dom";
import { X } from "lucide-react";
import { NAV_ITEMS } from "./navigation";
import styles from "./Sidebar.module.css";

export interface SidebarProps {
  /** Mobile drawer open state. Ignored (sidebar is always visible) at
   * desktop widths — see Sidebar.module.css. */
  open: boolean;
  onClose: () => void;
}

/** Primary navigation. Desktop: a fixed-width column. Mobile: an overlay
 * drawer toggled from the Topbar's menu button. */
export function Sidebar({ open, onClose }: SidebarProps) {
  return (
    <>
      {open && <div className={styles.scrim} onClick={onClose} aria-hidden="true" />}
      <nav
        aria-label="Primary"
        className={`${styles.sidebar} ${open ? styles.open : ""}`}
      >
        <div className={styles.header}>
          <span className={styles.brand}>Pharma Commercial Intelligence</span>
          <button type="button" className={styles.closeButton} onClick={onClose} aria-label="Close navigation">
            <X size={18} aria-hidden="true" />
          </button>
        </div>
        <ul className={styles.list}>
          {NAV_ITEMS.map((item) => {
            const Icon = item.icon;
            return (
              <li key={item.to}>
                <NavLink
                  to={item.to}
                  end={item.to === "/"}
                  className={({ isActive }) => `${styles.link} ${isActive ? styles.active : ""}`}
                  onClick={onClose}
                >
                  <Icon size={17} aria-hidden="true" />
                  <span>{item.label}</span>
                </NavLink>
              </li>
            );
          })}
        </ul>
      </nav>
    </>
  );
}
