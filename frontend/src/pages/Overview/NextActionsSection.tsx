import type { UseQueryResult } from "@tanstack/react-query";
import { ArrowRight } from "lucide-react";
import { Link } from "react-router-dom";
import { Card } from "../../components/ui/Card/Card";
import { SectionHeader } from "../../components/ui/SectionHeader/SectionHeader";
import type { AtcPerformanceResponse, DataQualityResponse, KpiSummary, RecommendationsResponse } from "../../types/api";
import styles from "./Overview.module.css";

export interface NextActionsSectionProps {
  kpiQuery: UseQueryResult<KpiSummary, unknown>;
  atcQuery: UseQueryResult<AtcPerformanceResponse, unknown>;
  dataQualityQuery: UseQueryResult<DataQualityResponse, unknown>;
  recommendationsQuery: UseQueryResult<RecommendationsResponse, unknown>;
}

interface ActionItem {
  key: string;
  label: string;
  to: string;
}

/** "What to investigate next" — every item is either conditioned on
 * real evidence surfaced elsewhere on this page (dominant class,
 * significant trend classes, a non-passing data-quality status) or a
 * standing link to another application section. Nothing here asserts a
 * recommendation as fact; each label names the evidence, the linked
 * page is where the stakeholder investigates it. */
export function NextActionsSection({ kpiQuery, atcQuery, dataQualityQuery, recommendationsQuery }: NextActionsSectionProps) {
  const actions: ActionItem[] = [];

  const dominant = kpiQuery.data?.dominant_atc_class;
  if (dominant) {
    actions.push({
      key: "dominant",
      label: `Investigate ${dominant} exposure — the dominant ATC class`,
      to: "/demand?tab=atc",
    });
  }

  const classes = atcQuery.data?.classes ?? [];
  const growing = classes.filter((c) => c.trend_classification === "growing");
  const declining = classes.filter((c) => c.trend_classification === "declining");

  if (growing.length > 0) {
    actions.push({
      key: "growing",
      label: `Review ${growing.map((c) => c.atc_class).join(", ")} — statistically significant growth`,
      to: `/forecast/${growing[0]!.atc_class}`,
    });
  }
  if (declining.length > 0) {
    actions.push({
      key: "declining",
      label: `Review ${declining.map((c) => c.atc_class).join(", ")} — statistically significant decline`,
      to: `/forecast/${declining[0]!.atc_class}`,
    });
  }

  if (dataQualityQuery.data && dataQualityQuery.data.overall_status !== "pass") {
    actions.push({
      key: "data-quality",
      label: "Review the data-quality reconciliation warning",
      to: "/data-quality",
    });
  }

  const lowConfidenceCount = (recommendationsQuery.data?.recommendations ?? []).filter((r) => r.confidence === "low").length;
  if (lowConfidenceCount > 0) {
    actions.push({
      key: "low-confidence",
      label: `Review ${lowConfidenceCount} low-confidence recommendation${lowConfidenceCount === 1 ? "" : "s"}`,
      to: "/recommendations",
    });
  }

  actions.push({ key: "forecast", label: "Review 14-day demand forecasts", to: "/forecast" });
  actions.push({ key: "planning", label: "Review supply-planning scenarios", to: "/planning" });

  return (
    <section aria-labelledby="next-actions-heading">
      <SectionHeader
        id="next-actions-heading"
        eyebrow="Action"
        title="Planning / Next Actions"
        description="What to investigate next, based on the evidence above."
      />
      <Card>
        <ul className={styles.actionList}>
          {actions.map((action) => (
            <li key={action.key}>
              <Link to={action.to} className={styles.actionLink}>
                <span>{action.label}</span>
                <ArrowRight size={14} aria-hidden="true" />
              </Link>
            </li>
          ))}
        </ul>
      </Card>
    </section>
  );
}
