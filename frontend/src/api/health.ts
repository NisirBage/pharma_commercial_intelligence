import { get } from "./client";
import { HealthSchema, type Health } from "../types/api";

export function getHealth(signal?: AbortSignal): Promise<Health> {
  return get("/health", HealthSchema, undefined, signal);
}
