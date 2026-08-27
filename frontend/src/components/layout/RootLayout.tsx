import { NavLink, Outlet } from "react-router-dom";

/**
 * Bare-bones navigational shell for M7.2 (scaffolding) — proves routing
 * and navigation work end to end. The visual application shell (Sidebar/
 * Topbar/PageContainer, per docs/frontend-architecture.md) is built out
 * in M7.3 without changing this component's structural role.
 */
const NAV_ITEMS: { to: string; label: string }[] = [
  { to: "/", label: "Overview" },
  { to: "/demand", label: "Demand Intelligence" },
  { to: "/forecast", label: "Forecasting" },
  { to: "/planning", label: "Supply Planning" },
  { to: "/recommendations", label: "Recommendations" },
  { to: "/data-quality", label: "Data Quality" },
];

export function RootLayout() {
  return (
    <div>
      <a href="#main-content" className="skip-link">
        Skip to main content
      </a>
      <header>
        <strong>Pharma Demand Intelligence &amp; Supply Planning</strong>
      </header>
      <nav aria-label="Primary">
        <ul>
          {NAV_ITEMS.map((item) => (
            <li key={item.to}>
              <NavLink to={item.to} end={item.to === "/"}>
                {item.label}
              </NavLink>
            </li>
          ))}
        </ul>
      </nav>
      <main id="main-content">
        <Outlet />
      </main>
    </div>
  );
}
