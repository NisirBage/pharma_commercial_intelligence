import { LayoutDashboard, LineChart, Lightbulb, Package, ShieldCheck, TrendingUp } from "lucide-react";
import type { LucideIcon } from "lucide-react";

export interface NavItem {
  to: string;
  label: string;
  icon: LucideIcon;
  /** Matches nested routes (e.g. /demand/atc/:atcClass) under this item's
   * section so the Sidebar and Topbar agree on the "current section". */
  matchPrefix?: string;
}

/**
 * The single source of truth for primary navigation — shared by Sidebar
 * (nav links) and Topbar (page title/breadcrumb derivation) so the two
 * never drift. Intentionally just the six domain sections from M7 Sec.
 * 10 — no Profile/Messages/Notifications/Billing/Settings.
 */
export const NAV_ITEMS: NavItem[] = [
  { to: "/", label: "Overview", icon: LayoutDashboard },
  { to: "/demand", label: "Demand Intelligence", icon: TrendingUp, matchPrefix: "/demand" },
  { to: "/forecast", label: "Forecasting", icon: LineChart, matchPrefix: "/forecast" },
  { to: "/planning", label: "Supply Planning", icon: Package },
  { to: "/recommendations", label: "Recommendations", icon: Lightbulb },
  { to: "/data-quality", label: "Data Quality", icon: ShieldCheck },
];

/** Finds the nav section a given pathname belongs to, for the Topbar's
 * page title and breadcrumb. Longest-prefix match so `/demand/atc/N02BE`
 * still resolves to "Demand Intelligence". */
export function matchNavItem(pathname: string): NavItem | undefined {
  const candidates = NAV_ITEMS.filter((item) => {
    const prefix = item.matchPrefix ?? item.to;
    if (prefix === "/") return pathname === "/";
    return pathname === prefix || pathname.startsWith(`${prefix}/`);
  });
  return candidates.sort((a, b) => (b.matchPrefix ?? b.to).length - (a.matchPrefix ?? a.to).length)[0];
}
