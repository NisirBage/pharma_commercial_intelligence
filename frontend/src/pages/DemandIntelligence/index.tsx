import { useSearchParams } from "react-router-dom";
import { SectionHeader } from "../../components/ui/SectionHeader/SectionHeader";
import { Tabs, type TabItem } from "../../components/ui/Tabs/Tabs";
import { AnomaliesSection } from "./AnomaliesSection";
import { AtcAnalysisSection } from "./AtcAnalysisSection";
import styles from "./DemandIntelligence.module.css";
import { SeasonalitySection } from "./SeasonalitySection";
import { TrendsSection } from "./TrendsSection";

const VALID_TABS = ["trends", "atc", "seasonality", "anomalies"] as const;
type DemandTab = (typeof VALID_TABS)[number];

function isValidTab(value: string | null): value is DemandTab {
  return value !== null && (VALID_TABS as readonly string[]).includes(value);
}

const TAB_ITEMS: TabItem[] = [
  { value: "trends", label: "Trends" },
  { value: "atc", label: "ATC Analysis" },
  { value: "seasonality", label: "Seasonality" },
  { value: "anomalies", label: "Anomalies" },
];

/**
 * Demand Intelligence — M7.5. One coherent analytical workspace across
 * four tabs (data -> demand -> forecast -> plan -> action's second
 * step), all reading the M3/M7.1.5 analytics endpoints directly. Only
 * the active tab's section is mounted, so switching tabs never fetches
 * data for a tab the user isn't looking at (M7.5 Sec. 18). The tab
 * itself is the one piece of state that persists in the URL
 * (`?tab=`); per-tab filters (ATC class, grain, date range, method,
 * severity) are local component state — URL-persisting every filter
 * would be over-engineering for what this milestone needs (M7.5 Sec.
 * 12), so a tab switch or refresh resets a tab's own filters but never
 * loses which tab you're on.
 */
export function DemandIntelligencePage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const tabParam = searchParams.get("tab");
  const activeTab: DemandTab = isValidTab(tabParam) ? tabParam : "trends";

  function handleTabChange(value: string) {
    setSearchParams((prev) => {
      const next = new URLSearchParams(prev);
      next.set("tab", value);
      return next;
    });
  }

  return (
    <div className={styles.page}>
      <SectionHeader
        as="h1"
        title="Demand Intelligence"
        description="How demand has moved, which classes drive it, what seasonal patterns recur, and where the unusual observations are."
      />

      <Tabs items={TAB_ITEMS} value={activeTab} onChange={handleTabChange} ariaLabel="Demand Intelligence sections" />

      <div
        id={`tabpanel-${activeTab}`}
        role="tabpanel"
        aria-labelledby={`tab-${activeTab}`}
        tabIndex={0}
        className={styles.tabPanel}
      >
        {activeTab === "trends" && <TrendsSection />}
        {activeTab === "atc" && <AtcAnalysisSection />}
        {activeTab === "seasonality" && <SeasonalitySection />}
        {activeTab === "anomalies" && <AnomaliesSection />}
      </div>
    </div>
  );
}
