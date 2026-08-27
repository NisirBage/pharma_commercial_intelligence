import { useSearchParams } from "react-router-dom";

const VALID_TABS = ["trends", "atc", "seasonality", "anomalies"] as const;
type DemandTab = (typeof VALID_TABS)[number];

function isValidTab(value: string | null): value is DemandTab {
  return value !== null && (VALID_TABS as readonly string[]).includes(value);
}

export function DemandIntelligencePage() {
  const [searchParams] = useSearchParams();
  const tabParam = searchParams.get("tab");
  const activeTab: DemandTab = isValidTab(tabParam) ? tabParam : "trends";

  return (
    <section>
      <h1>Demand Intelligence</h1>
      <p>Active tab: {activeTab}</p>
      <p>Scaffolding placeholder — implemented in M7.5.</p>
    </section>
  );
}
