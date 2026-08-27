import { useState } from "react";
import { SectionHeader } from "../../components/ui/SectionHeader/SectionHeader";
import { useOptimizationRun } from "../../hooks/useOptimizationRun";
import { useOptimizationScenarios } from "../../hooks/useOptimizationScenarios";
import type { RunOptimizationBody } from "../../api/optimization";
import type { OptimizationRunResponse, ScenarioName } from "../../types/api";
import { OptimizationSummary } from "./OptimizationSummary";
import { RecommendedPlanTable } from "./RecommendedPlanTable";
import { ScenarioForm } from "./ScenarioForm";
import { SensitivitySection } from "./SensitivitySection";
import styles from "./SupplyPlanning.module.css";

function bodiesEqual(a: RunOptimizationBody | undefined, b: RunOptimizationBody): boolean {
  if (!a) return false;
  return a.scenario === b.scenario && a.service_level === b.service_level && a.lead_time_days === b.lead_time_days;
}

interface SuccessfulRun {
  body: RunOptimizationBody;
  response: OptimizationRunResponse;
}

/**
 * Supply Planning & Optimization — M7.7. A decision-support surface
 * around M5's cross-class safety-stock LP: pick a scenario (optionally
 * overriding service level / lead time), run the optimizer, and read
 * the recommendation, its objective value, and how sensitive it is to
 * the inputs that drive it.
 *
 * POST /api/v1/optimization/run is a `useMutation`, never auto-fired —
 * a run only happens when the user clicks Run. State is kept in four
 * explicitly separate pieces, per M7.7 Sec. 8: the current form
 * configuration (local state below), the last SUCCESSFUL result
 * (`lastSuccess`, set only in `onSuccess` — deliberately NOT read from
 * `runMutation.data`, which does not reliably survive a subsequent
 * failed call), the running state (`runMutation.isPending`), and the
 * error state (`runMutation.isError`/`.error`). A failed run therefore
 * never clears a previously-successful result, and editing the form
 * without re-running flags the shown result as stale (`isStale`)
 * rather than silently presenting it as current.
 */
export function SupplyPlanningPage() {
  const scenariosQuery = useOptimizationScenarios();
  const runMutation = useOptimizationRun();

  const [scenario, setScenario] = useState<ScenarioName>("balanced");
  const [serviceLevelPct, setServiceLevelPct] = useState("");
  const [leadTimeDays, setLeadTimeDays] = useState("");
  const [lastSuccess, setLastSuccess] = useState<SuccessfulRun | null>(null);

  const serviceLevelError =
    serviceLevelPct !== "" && (Number(serviceLevelPct) < 1 || Number(serviceLevelPct) > 99 || !Number.isFinite(Number(serviceLevelPct)))
      ? "Enter a whole percent between 1 and 99."
      : undefined;
  const leadTimeError =
    leadTimeDays !== "" && (Number(leadTimeDays) < 0 || Number(leadTimeDays) > 14 || !Number.isInteger(Number(leadTimeDays)))
      ? "Enter a whole number of days from 0 to 14."
      : undefined;
  const isFormValid = !serviceLevelError && !leadTimeError;

  const currentBody: RunOptimizationBody = {
    scenario,
    service_level: serviceLevelPct !== "" ? Number(serviceLevelPct) / 100 : undefined,
    lead_time_days: leadTimeDays !== "" ? Number(leadTimeDays) : undefined,
  };

  const isStale = lastSuccess !== null && !bodiesEqual(lastSuccess.body, currentBody);
  const selectedScenarioInfo = scenariosQuery.data?.scenarios.find((s) => s.name === scenario);

  function handleRun() {
    if (!isFormValid) return;
    runMutation.mutate(currentBody, {
      onSuccess: (response) => setLastSuccess({ body: currentBody, response }),
    });
  }

  function handleRetry() {
    if (runMutation.variables) {
      runMutation.mutate(runMutation.variables, {
        onSuccess: (response) => {
          if (runMutation.variables) setLastSuccess({ body: runMutation.variables, response });
        },
      });
    }
  }

  return (
    <div className={styles.page}>
      <SectionHeader
        as="h1"
        title="Supply Planning & Optimization"
        description="A scenario simulation of how a shared safety-stock budget could be allocated across ATC classes — not a claim about real current inventory (see Assumptions below)."
      />

      <ScenarioForm
        scenariosQuery={scenariosQuery}
        scenario={scenario}
        onScenarioChange={setScenario}
        serviceLevelPct={serviceLevelPct}
        onServiceLevelPctChange={setServiceLevelPct}
        leadTimeDays={leadTimeDays}
        onLeadTimeDaysChange={setLeadTimeDays}
        onRun={handleRun}
        isRunning={runMutation.isPending}
        serviceLevelError={serviceLevelError}
        leadTimeError={leadTimeError}
      />

      <OptimizationSummary
        result={lastSuccess?.response ?? null}
        isPending={runMutation.isPending}
        isError={runMutation.isError}
        error={runMutation.error}
        isStale={isStale}
        onRetry={handleRetry}
      />

      <RecommendedPlanTable result={lastSuccess?.response ?? null} isPending={runMutation.isPending} />

      <SensitivitySection scenario={scenario} scenarioInfo={selectedScenarioInfo} />
    </div>
  );
}
