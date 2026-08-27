import { useState } from "react";
import { Outlet } from "react-router-dom";
import { Sidebar } from "./Sidebar";
import { Topbar } from "./Topbar";
import { PageContainer } from "./PageContainer";
import styles from "./AppShell.module.css";

/**
 * The application shell: Sidebar + Topbar + main content area. Owns only
 * the mobile drawer's open/closed state — no global state library, no
 * fetched data (M7.3 Sec. 27 "avoid unnecessary providers/global
 * state"). Every route renders inside this via the router's layout
 * route (see routes/router.tsx / RootLayout.tsx).
 */
export function AppShell() {
  const [mobileNavOpen, setMobileNavOpen] = useState(false);

  return (
    <div className={styles.shell}>
      <a href="#main-content" className="skip-link">
        Skip to main content
      </a>
      <Sidebar open={mobileNavOpen} onClose={() => setMobileNavOpen(false)} />
      <div className={styles.main}>
        <Topbar onMenuClick={() => setMobileNavOpen(true)} />
        <main id="main-content" className={styles.content}>
          <PageContainer>
            <Outlet />
          </PageContainer>
        </main>
      </div>
    </div>
  );
}
