import { createBrowserRouter } from "react-router-dom";
import { RootLayout } from "../components/layout/RootLayout";
import { OverviewPage } from "../pages/Overview";
import { DemandIntelligencePage } from "../pages/DemandIntelligence";
import { AtcDetailPage } from "../pages/AtcDetail";
import { ForecastingPage } from "../pages/Forecasting";
import { SupplyPlanningPage } from "../pages/SupplyPlanning";
import { RecommendationsPage } from "../pages/Recommendations";
import { DataQualityPage } from "../pages/DataQuality";
import { NotFoundPage } from "../pages/NotFound";

/**
 * Route map (M7 Sec. 8/10). Demand Intelligence and Forecasting are each
 * ONE page with internal state (tabs via `?tab=`, optional `:atcClass`)
 * rather than fragmented per sub-section — matches the brief's own
 * "combine related information" instruction and keeps the
 * data -> demand -> forecast -> plan -> recommend story navigable in a
 * handful of clicks.
 */
export const router = createBrowserRouter([
  {
    path: "/",
    element: <RootLayout />,
    children: [
      { index: true, element: <OverviewPage /> },
      { path: "demand", element: <DemandIntelligencePage /> },
      { path: "demand/atc/:atcClass", element: <AtcDetailPage /> },
      { path: "forecast", element: <ForecastingPage /> },
      { path: "forecast/:atcClass", element: <ForecastingPage /> },
      { path: "planning", element: <SupplyPlanningPage /> },
      { path: "recommendations", element: <RecommendationsPage /> },
      { path: "data-quality", element: <DataQualityPage /> },
      { path: "*", element: <NotFoundPage /> },
    ],
  },
]);
