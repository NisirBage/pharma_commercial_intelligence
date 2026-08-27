import { get, post } from "./client";
import {
  ScenariosResponseSchema,
  SensitivityResponseSchema,
  OptimizationRunResponseSchema,
  type ScenariosResponse,
  type SensitivityResponse,
  type SensitivityParameter,
  type OptimizationRunResponse,
  type ScenarioName,
} from "../types/api";

export function getOptimizationScenarios(signal?: AbortSignal): Promise<ScenariosResponse> {
  return get("/api/v1/optimization/scenarios", ScenariosResponseSchema, undefined, signal);
}

export interface GetSensitivityParams {
  atcClass: string;
  scenario?: ScenarioName;
  parameter: SensitivityParameter;
}

export function getOptimizationSensitivity(params: GetSensitivityParams, signal?: AbortSignal): Promise<SensitivityResponse> {
  return get(
    "/api/v1/optimization/sensitivity",
    SensitivityResponseSchema,
    { atc_class: params.atcClass, scenario: params.scenario, parameter: params.parameter },
    signal,
  );
}

export interface RunOptimizationBody {
  scenario?: ScenarioName;
  service_level?: number;
  lead_time_days?: number;
}

/** POST /api/v1/optimization/run — runs M5's real LP against the cached
 * demand-input layer. Every result is a SCENARIO SIMULATION, never an
 * observed fact — see OptimizationRunResponse.assumptions in the caller. */
export function runOptimization(body: RunOptimizationBody, signal?: AbortSignal): Promise<OptimizationRunResponse> {
  return post("/api/v1/optimization/run", OptimizationRunResponseSchema, body, signal);
}
