import { useAtcAnalytics } from "../../hooks/useAtcAnalytics";
import { useDataQuality } from "../../hooks/useDataQuality";
import { useForecast } from "../../hooks/useForecast";
import { useHealth } from "../../hooks/useHealth";
import { useKpiSummary } from "../../hooks/useKpiSummary";
import { useOptimizationScenarios } from "../../hooks/useOptimizationScenarios";
import { useRecommendations } from "../../hooks/useRecommendations";
import { SectionHeader } from "../../components/ui/SectionHeader/SectionHeader";
import { CommercialSignalsSection } from "./CommercialSignalsSection";
import { ConcentrationSection } from "./ConcentrationSection";
import { DataQualitySection } from "./DataQualitySection";
import { DemandPositionSection } from "./DemandPositionSection";
import { ForecastPreviewSection } from "./ForecastPreviewSection";
import { KpiSummarySection } from "./KpiSummarySection";
import { NextActionsSection } from "./NextActionsSection";
import { RecommendationsPreviewSection } from "./RecommendationsPreviewSection";
import { SupplyPlanningPreviewSection } from "./SupplyPlanningPreviewSection";
import styles from "./Overview.module.css";

/**
 * Executive Overview — M7.4, extended in M7.9 to preview the four
 * intelligence surfaces built since (Demand, Forecasting, Supply
 * Planning, Recommendations) so the app reads as one coherent product
 * rather than five disconnected pages. Every number on this page traces
 * back to one of seven independent GET queries — KPI summary, ATC
 * analytics, data quality, health, aggregate forecast, planning
 * scenarios, and recommendations; each is fetched here and handed down
 * to its own section so one endpoint failing never blanks the sections
 * that don't depend on it. The forecast/scenarios/recommendations
 * queries reuse the exact hooks and query keys their own detail pages
 * use, so visiting /forecast, /planning, or /recommendations right
 * after Overview is typically a cache hit, not a second request. No
 * mutation (POST /optimization/run) is ever called here — see
 * SupplyPlanningPreviewSection for why that section shows scenario
 * definitions rather than a fabricated result. See
 * docs/frontend-executive-intelligence-page.md for the full API -> UI
 * mapping.
 */
export function OverviewPage() {
  const kpiQuery = useKpiSummary();
  const atcQuery = useAtcAnalytics();
  const dataQualityQuery = useDataQuality();
  const healthQuery = useHealth();
  const forecastQuery = useForecast(undefined);
  const scenariosQuery = useOptimizationScenarios();
  const recommendationsQuery = useRecommendations();

  return (
    <div className={styles.page}>
      <SectionHeader
        as="h1"
        title="Executive Overview"
        description="Commercial demand, forecast, planning, and recommendation signals in one view."
      />

      <KpiSummarySection query={kpiQuery} />

      <DemandPositionSection kpiQuery={kpiQuery} atcQuery={atcQuery} />

      <ConcentrationSection query={atcQuery} />

      <CommercialSignalsSection query={atcQuery} />

      <ForecastPreviewSection query={forecastQuery} />

      <SupplyPlanningPreviewSection query={scenariosQuery} />

      <RecommendationsPreviewSection query={recommendationsQuery} />

      <DataQualitySection query={dataQualityQuery} healthQuery={healthQuery} />

      <NextActionsSection
        kpiQuery={kpiQuery}
        atcQuery={atcQuery}
        dataQualityQuery={dataQualityQuery}
        recommendationsQuery={recommendationsQuery}
      />
    </div>
  );
}
