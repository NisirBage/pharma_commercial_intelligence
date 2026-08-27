/**
 * Centralized HTTP client. Every api/*.ts module goes through this —
 * nothing in the app calls `fetch` directly. Three distinct, typed error
 * classes so callers (and hooks/components) can react differently to
 * "the backend told us something is wrong" vs. "the backend responded
 * with something that doesn't match its own documented contract" vs.
 * "we couldn't reach the backend at all" — never a single generic Error.
 */

import { z } from "zod";
import { ErrorResponseSchema, ResponseMetadataSchema } from "../types/api";

const API_BASE_URL: string = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

/** The backend told us, in its own error envelope, that the request failed. */
export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly details: { field?: string | null; message: string }[];

  constructor(status: number, code: string, message: string, details: { field?: string | null; message: string }[] = []) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.details = details;
  }
}

/** The response's HTTP status was OK, but its shape didn't match the
 * schema mirrored from the backend's own Pydantic model — a contract
 * drift, not a business error. Never rendered as partial/best-effort
 * data (see M6 Sec. 31 / the M7 "never invent data" rule). */
export class ApiValidationError extends Error {
  readonly path: string;
  readonly issues: z.ZodIssue[];

  constructor(path: string, issues: z.ZodIssue[]) {
    super(`The response for ${path} did not match the expected contract.`);
    this.name = "ApiValidationError";
    this.path = path;
    this.issues = issues;
  }
}

/** fetch() itself failed — offline, DNS, connection refused, CORS, etc. */
export class ApiNetworkError extends Error {
  constructor(message = "Unable to reach the API. Check your connection or that the backend is running.") {
    super(message);
    this.name = "ApiNetworkError";
  }
}

export type QueryParams = Record<string, string | number | boolean | undefined | null>;

interface RequestOptions {
  method?: "GET" | "POST";
  params?: QueryParams;
  body?: unknown;
  signal?: AbortSignal;
}

function buildUrl(path: string, params?: QueryParams): string {
  const url = new URL(path, API_BASE_URL);
  if (params) {
    for (const [key, value] of Object.entries(params)) {
      if (value !== undefined && value !== null) {
        url.searchParams.set(key, String(value));
      }
    }
  }
  return url.toString();
}

async function apiRequest<T>(path: string, dataSchema: z.ZodType<T>, options: RequestOptions = {}): Promise<T> {
  const { method = "GET", params, body, signal } = options;
  const url = buildUrl(path, params);

  let response: Response;
  try {
    response = await fetch(url, {
      method,
      headers: body !== undefined ? { "Content-Type": "application/json" } : undefined,
      body: body !== undefined ? JSON.stringify(body) : undefined,
      signal,
    });
  } catch (err) {
    if (err instanceof DOMException && err.name === "AbortError") {
      throw err; // query cancellation — let TanStack Query handle it, not an app-level error
    }
    throw new ApiNetworkError();
  }

  let json: unknown;
  try {
    json = await response.json();
  } catch {
    if (response.ok) {
      throw new ApiNetworkError("The server returned an unreadable response.");
    }
    throw new ApiError(response.status, "unknown_error", `Request failed with status ${response.status}.`);
  }

  if (!response.ok) {
    const parsedError = ErrorResponseSchema.safeParse(json);
    if (parsedError.success) {
      const { code, message, details } = parsedError.data.error;
      throw new ApiError(response.status, code, message, details);
    }
    throw new ApiError(response.status, "unknown_error", `Request failed with status ${response.status}.`);
  }

  const envelopeSchema = z.object({ data: dataSchema, metadata: ResponseMetadataSchema });
  const parsed = envelopeSchema.safeParse(json);
  if (!parsed.success) {
    // Logged for development debugging; never exposes internal details to the UI itself.
    console.error(`[api] contract validation failed for ${path}`, parsed.error.issues);
    throw new ApiValidationError(path, parsed.error.issues);
  }
  return parsed.data.data;
}

export function get<T>(path: string, dataSchema: z.ZodType<T>, params?: QueryParams, signal?: AbortSignal): Promise<T> {
  return apiRequest(path, dataSchema, { method: "GET", params, signal });
}

export function post<T>(path: string, dataSchema: z.ZodType<T>, body: unknown, signal?: AbortSignal): Promise<T> {
  return apiRequest(path, dataSchema, { method: "POST", body, signal });
}

/** Human-readable message for any error this client can throw — the one
 * place UI copy for API failures is written, so every page's error state
 * is consistent (M7 error-handling rules: never a raw stack trace). */
export function describeApiError(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.status === 503) return "This service is temporarily unavailable. Please try again shortly.";
    if (error.status === 404) return error.message || "The requested resource was not found.";
    if (error.status === 422 || error.status === 400) return error.message || "The request could not be processed.";
    return error.message || "The request failed.";
  }
  if (error instanceof ApiValidationError) {
    return "The server returned data in an unexpected format. This has been logged for investigation.";
  }
  if (error instanceof ApiNetworkError) {
    return error.message;
  }
  return "An unexpected error occurred.";
}
