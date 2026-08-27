import { useState } from "react";
import { EmptyState } from "../../components/ui/EmptyState/EmptyState";
import { ErrorState } from "../../components/ui/ErrorState/ErrorState";
import { MetricCard } from "../../components/ui/MetricCard/MetricCard";
import { SectionHeader } from "../../components/ui/SectionHeader/SectionHeader";
import { Select } from "../../components/ui/Select/Select";
import { Skeleton } from "../../components/ui/Skeleton/Skeleton";
import { useRecommendations } from "../../hooks/useRecommendations";
import type { ScenarioName } from "../../types/api";
import { RecommendationCard } from "./RecommendationCard";
import styles from "./Recommendations.module.css";

const SCENARIO_OPTIONS: { value: ScenarioName; label: string }[] = [
  { value: "conservative", label: "Conservative" },
  { value: "balanced", label: "Balanced" },
  { value: "lean", label: "Lean" },
];

// The 3 confidence values GET /api/v1/recommendations can return are a
// fixed enum in app/optimization/recommendations.py's
// _confidence_from_model_evidence — not loaded from any endpoint (there
// isn't one), same as M7.5's anomaly-severity options.
const CONFIDENCE_FILTER_OPTIONS = [
  { value: "", label: "All confidence levels" },
  { value: "low", label: "Low" },
  { value: "medium", label: "Medium" },
  { value: "medium-high", label: "Medium-high" },
];

/**
 * Recommendations Intelligence — M7.8. Exactly one explainable
 * recommendation per observed ATC class (never an aggregate item),
 * combining M3 demand/volatility findings, M4's own model-selection
 * evidence (which drives `confidence` — a 3-value categorical string,
 * never a numeric score), and M5's per-class reorder-point calculation.
 * GET-only, `scenario` the one server-side filter; confidence filtering
 * is client-side (the response is at most 8 items, and no server
 * parameter exists for it) and never mutates the fetched array.
 */
export function RecommendationsPage() {
  const [scenario, setScenario] = useState<ScenarioName>("balanced");
  const [confidenceFilter, setConfidenceFilter] = useState("");

  const { data, isLoading, isError, error, refetch } = useRecommendations(scenario);
  const recommendations = data?.recommendations ?? [];
  const filtered = confidenceFilter ? recommendations.filter((r) => r.confidence === confidenceFilter) : recommendations;

  const lowCount = recommendations.filter((r) => r.confidence === "low").length;
  const mediumCount = recommendations.filter((r) => r.confidence === "medium").length;
  const mediumHighCount = recommendations.filter((r) => r.confidence === "medium-high").length;

  return (
    <div className={styles.page}>
      <SectionHeader
        as="h1"
        title="Recommendations Intelligence"
        description="Explainable, per-ATC-class planning guidance — each recommendation names its own evidence, assumptions, expected effect, confidence, and limitations. Informational, not an executable action: the API has no endpoint to apply one."
      />

      <div className={styles.controls}>
        <div className={styles.controlField}>
          <Select
            label="Planning scenario"
            options={SCENARIO_OPTIONS}
            value={scenario}
            onChange={(e) => setScenario(e.target.value as ScenarioName)}
          />
        </div>
        <div className={styles.controlField}>
          <Select
            label="Filter by confidence"
            options={CONFIDENCE_FILTER_OPTIONS}
            value={confidenceFilter}
            onChange={(e) => setConfidenceFilter(e.target.value)}
            helperText="Filters the list below only — does not change the scenario or re-query the API."
          />
        </div>
      </div>

      {isError ? (
        <ErrorState title="Couldn't load recommendations" error={error} onRetry={() => refetch()} />
      ) : isLoading ? (
        <div className={styles.sectionStack}>
          <div className={styles.kpiGrid}>
            <MetricCard label="Total Recommendations" loading />
            <MetricCard label="Low Confidence" loading />
            <MetricCard label="Medium Confidence" loading />
            <MetricCard label="Medium-High Confidence" loading />
          </div>
          <Skeleton variant="card" />
          <Skeleton variant="card" />
        </div>
      ) : recommendations.length === 0 ? (
        <EmptyState
          title="No recommendations available"
          description="The API returned no recommendations for this scenario."
        />
      ) : (
        <div className={styles.sectionStack}>
          <div className={styles.kpiGrid}>
            <MetricCard label="Total Recommendations" value={String(recommendations.length)} helperText={`Scenario: ${data?.scenario ?? scenario}`} />
            <MetricCard label="Low Confidence" value={String(lowCount)} helperText="Recommendations to scrutinize most" />
            <MetricCard label="Medium Confidence" value={String(mediumCount)} />
            <MetricCard label="Medium-High Confidence" value={String(mediumHighCount)} helperText="Most reliable tier available" />
          </div>

          {filtered.length === 0 ? (
            <EmptyState
              title="No recommendations match this filter"
              description="Choose a different confidence level, or select 'All confidence levels' to see everything returned for this scenario."
            />
          ) : (
            <div className={styles.cardList}>
              {filtered.map((item) => (
                <RecommendationCard key={item.atc_class} item={item} />
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
