import { useAtcAnalytics } from "../../hooks/useAtcAnalytics";
import { useDataQuality } from "../../hooks/useDataQuality";
import { useHealth } from "../../hooks/useHealth";
import { useKpiSummary } from "../../hooks/useKpiSummary";
import { SectionHeader } from "../../components/ui/SectionHeader/SectionHeader";
import { CommercialSignalsSection } from "./CommercialSignalsSection";
import { ConcentrationSection } from "./ConcentrationSection";
import { DataQualitySection } from "./DataQualitySection";
import { DemandPositionSection } from "./DemandPositionSection";
import { KpiSummarySection } from "./KpiSummarySection";
import { NextActionsSection } from "./NextActionsSection";
import styles from "./Overview.module.css";

/**
 * Executive Overview — M7.4. Every number on this page traces back to
 * one of four independent queries (KPI summary, ATC analytics, data
 * quality, health); each is fetched here and handed down to its
 * section so one endpoint failing never blanks the sections that don't
 * depend on it. No business value is computed or fabricated in this
 * file or its sections — see docs/frontend-design-system.md "Overview
 * data sources" for the full API -> UI mapping.
 */
export function OverviewPage() {
  const kpiQuery = useKpiSummary();
  const atcQuery = useAtcAnalytics();
  const dataQualityQuery = useDataQuality();
  const healthQuery = useHealth();

  return (
    <div className={styles.page}>
      <SectionHeader
        as="h1"
        title="Executive Overview"
        description="Commercial demand, concentration, and planning signals."
      />

      <KpiSummarySection query={kpiQuery} />

      <DemandPositionSection kpiQuery={kpiQuery} atcQuery={atcQuery} />

      <ConcentrationSection query={atcQuery} />

      <CommercialSignalsSection query={atcQuery} />

      <DataQualitySection query={dataQualityQuery} healthQuery={healthQuery} />

      <NextActionsSection kpiQuery={kpiQuery} atcQuery={atcQuery} dataQualityQuery={dataQualityQuery} />
    </div>
  );
}
