import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";
import { server } from "../mocks/server";
import { KpiSummarySchema } from "../types/api";
import { ApiError, ApiNetworkError, ApiValidationError, describeApiError, get } from "./client";

const KPI_URL = "http://localhost:8000/api/v1/kpis/summary";

describe("api client", () => {
  it("parses a valid success envelope and returns the data payload", async () => {
    const result = await get("/api/v1/kpis/summary", KpiSummarySchema);
    expect(result.dominant_atc_class).toBe("N02BE");
    expect(result.period.start).toBe("2014-01-02");
  });

  it("throws ApiError with the backend's own code/message on a 404 error envelope", async () => {
    server.use(
      http.get(KPI_URL, () =>
        HttpResponse.json(
          { error: { code: "not_found", message: "Unknown ATC class.", details: [] } },
          { status: 404 },
        ),
      ),
    );

    await expect(get("/api/v1/kpis/summary", KpiSummarySchema)).rejects.toMatchObject({
      name: "ApiError",
      status: 404,
      code: "not_found",
    });
  });

  it("throws ApiError for a non-2xx response that isn't in the documented error envelope shape", async () => {
    server.use(http.get(KPI_URL, () => new HttpResponse("Internal Server Error", { status: 500 })));

    await expect(get("/api/v1/kpis/summary", KpiSummarySchema)).rejects.toBeInstanceOf(ApiError);
  });

  it("throws ApiValidationError when a 200 response doesn't match the expected contract", async () => {
    server.use(
      http.get(KPI_URL, () =>
        HttpResponse.json({
          data: { totally_wrong_field: 1 },
          metadata: { generated_at: new Date().toISOString() },
        }),
      ),
    );

    await expect(get("/api/v1/kpis/summary", KpiSummarySchema)).rejects.toBeInstanceOf(ApiValidationError);
  });

  it("throws ApiNetworkError when the request cannot reach the server", async () => {
    server.use(http.get(KPI_URL, () => HttpResponse.error()));

    await expect(get("/api/v1/kpis/summary", KpiSummarySchema)).rejects.toBeInstanceOf(ApiNetworkError);
  });

  it("never renders partial data on a validation failure — the promise rejects, nothing is returned", async () => {
    server.use(
      http.get(KPI_URL, () => HttpResponse.json({ data: null, metadata: { generated_at: "x" } })),
    );

    let resolved: unknown = "not-called";
    try {
      resolved = await get("/api/v1/kpis/summary", KpiSummarySchema);
    } catch {
      resolved = "rejected";
    }
    expect(resolved).toBe("rejected");
  });
});

describe("describeApiError", () => {
  it("gives a human-readable 503 message without leaking internals", () => {
    const message = describeApiError(new ApiError(503, "service_unavailable", "Forecasting models are not available yet — run backend/scripts/run_m4_backtest.py."));
    expect(message).toBe("This service is temporarily unavailable. Please try again shortly.");
  });

  it("passes through a 404 message from the backend", () => {
    const message = describeApiError(new ApiError(404, "not_found", "Unknown ATC class 'ZZZ'."));
    expect(message).toBe("Unknown ATC class 'ZZZ'.");
  });

  it("never exposes Zod issue internals for a validation error", () => {
    const message = describeApiError(new ApiValidationError("/api/v1/kpis/summary", []));
    expect(message).not.toContain("ZodIssue");
    expect(message.length).toBeGreaterThan(0);
  });

  it("handles an unrecognized error type gracefully", () => {
    expect(describeApiError(new Error("boom"))).toBe("An unexpected error occurred.");
  });
});
