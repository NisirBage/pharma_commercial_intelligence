import type { UseQueryResult } from "@tanstack/react-query";
import { Play } from "lucide-react";
import { Button } from "../../components/ui/Button/Button";
import { ErrorState } from "../../components/ui/ErrorState/ErrorState";
import { Select } from "../../components/ui/Select/Select";
import { Skeleton } from "../../components/ui/Skeleton/Skeleton";
import type { ScenariosResponse, ScenarioName } from "../../types/api";
import { NumberField } from "./NumberField";
import styles from "./SupplyPlanning.module.css";

export interface ScenarioFormProps {
  scenariosQuery: UseQueryResult<ScenariosResponse, unknown>;
  scenario: ScenarioName;
  onScenarioChange: (scenario: ScenarioName) => void;
  serviceLevelPct: string;
  onServiceLevelPctChange: (value: string) => void;
  leadTimeDays: string;
  onLeadTimeDaysChange: (value: string) => void;
  onRun: () => void;
  isRunning: boolean;
  serviceLevelError?: string;
  leadTimeError?: string;
}

/**
 * Scenario selection + optional overrides, loaded from GET
 * /api/v1/optimization/scenarios rather than hardcoded — the 3 named
 * scenarios and their rationale text are the API's own words, not this
 * component's. `service_level`/`lead_time_days` are the only two
 * override fields OptimizationRunRequest actually accepts (verified in
 * backend/app/schemas/optimization.py); no other planning input exists
 * to expose a control for.
 */
export function ScenarioForm({
  scenariosQuery,
  scenario,
  onScenarioChange,
  serviceLevelPct,
  onServiceLevelPctChange,
  leadTimeDays,
  onLeadTimeDaysChange,
  onRun,
  isRunning,
  serviceLevelError,
  leadTimeError,
}: ScenarioFormProps) {
  const { data, isLoading, isError, error, refetch } = scenariosQuery;

  if (isError) {
    return <ErrorState title="Couldn't load planning scenarios" error={error} onRetry={() => refetch()} />;
  }

  if (isLoading) {
    return <Skeleton variant="text" count={3} />;
  }

  const scenarios = data?.scenarios ?? [];
  const selected = scenarios.find((s) => s.name === scenario);

  return (
    <div className={styles.sectionStack}>
      <div className={styles.controls}>
        <div className={styles.controlField}>
          <Select
            label="Planning scenario"
            options={scenarios.map((s) => ({ value: s.name, label: `${s.name[0]!.toUpperCase()}${s.name.slice(1)}` }))}
            value={scenario}
            // The Select's options are populated directly from this
            // same scenarios list, so every value it can emit is a
            // real ScenarioName the backend defined.
            onChange={(e) => onScenarioChange(e.target.value as ScenarioName)}
          />
        </div>

        <NumberField
          label="Service level override"
          value={serviceLevelPct}
          onChange={onServiceLevelPctChange}
          min={1}
          max={99}
          unit="%"
          placeholder={selected ? `${(selected.service_level_target * 100).toFixed(0)} (scenario default)` : undefined}
          helperText="Optional. Backend accepts any value strictly between 0% and 100%; leave blank to use the scenario's own target."
          error={serviceLevelError}
        />

        <NumberField
          label="Lead time override"
          value={leadTimeDays}
          onChange={onLeadTimeDaysChange}
          min={0}
          max={14}
          unit="days"
          placeholder={selected ? `${selected.lead_time_days} (scenario default)` : undefined}
          helperText="Optional, 0–14 days (the forecast horizon). Leave blank to use the scenario's own lead time."
          error={leadTimeError}
        />

        <div className={styles.runRow}>
          <Button
            variant="primary"
            icon={<Play size={16} aria-hidden="true" />}
            loading={isRunning}
            disabled={Boolean(serviceLevelError || leadTimeError)}
            onClick={onRun}
          >
            {isRunning ? "Running optimization…" : "Run optimization"}
          </Button>
        </div>
      </div>

      {selected && <p className={styles.scenarioRationale}>{selected.rationale}</p>}
    </div>
  );
}
