import { describe, expect, it } from "vitest";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { QueryClientProvider } from "@tanstack/react-query";
import { createMemoryRouter, RouterProvider } from "react-router-dom";
import { server } from "../../mocks/server";
import { createTestQueryClient, renderWithProviders } from "../../test/testUtils";
import { DemandIntelligencePage } from "./index";

const API_BASE_URL = "http://localhost:8000";

function envelope<T>(data: T) {
  return { data, metadata: { generated_at: new Date().toISOString(), source: "test-fixture" } };
}

function renderAt(route: string) {
  return renderWithProviders(<DemandIntelligencePage />, { route });
}

describe("DemandIntelligencePage — tabs", () => {
  it("defaults to the Trends tab at /demand", async () => {
    renderAt("/demand");
    expect(screen.getByRole("tab", { name: "Trends", selected: true })).toBeInTheDocument();
    expect(await screen.findByText("Demand Trends")).toBeInTheDocument();
  });

  it("shows the ATC Analysis tab for ?tab=atc", async () => {
    renderAt("/demand?tab=atc");
    expect(screen.getByRole("tab", { name: "ATC Analysis", selected: true })).toBeInTheDocument();
    expect(await screen.findByRole("heading", { name: "ATC Analysis" })).toBeInTheDocument();
  });

  it("shows the Seasonality tab for ?tab=seasonality", async () => {
    renderAt("/demand?tab=seasonality");
    expect(screen.getByRole("tab", { name: "Seasonality", selected: true })).toBeInTheDocument();
    expect(await screen.findByText("Weekly Seasonal Strength")).toBeInTheDocument();
  });

  it("shows the Anomalies tab for ?tab=anomalies", async () => {
    renderAt("/demand?tab=anomalies");
    expect(screen.getByRole("tab", { name: "Anomalies", selected: true })).toBeInTheDocument();
    expect(await screen.findByText("Anomalies Detected")).toBeInTheDocument();
  });

  it("falls back to Trends for an unrecognized ?tab value", () => {
    renderAt("/demand?tab=nonsense");
    expect(screen.getByRole("tab", { name: "Trends", selected: true })).toBeInTheDocument();
  });
});

describe("DemandIntelligencePage — Trends tab", () => {
  it("renders trend data from the API", async () => {
    // Recharts renders the line as an SVG path, not visible DOM text —
    // so this asserts on the derived summary (average/peak/count of
    // the exact points the fixture returned: 58.4, 61.2, 55.9), which
    // only matches if the chart actually received that API data.
    renderAt("/demand?tab=trends");
    expect(await screen.findByText("3")).toBeInTheDocument(); // Observations
    expect(screen.getByText("58.5")).toBeInTheDocument(); // average of 58.4/61.2/55.9
    expect(screen.getByText(/Peak 61\.2/)).toBeInTheDocument();
  });

  it("shows a loading state before data arrives", () => {
    renderAt("/demand?tab=trends");
    expect(screen.getAllByRole("status", { name: "Loading" }).length).toBeGreaterThan(0);
  });

  it("shows an error state on API failure, with retry", async () => {
    server.use(
      http.get(`${API_BASE_URL}/api/v1/sales/trends`, () =>
        HttpResponse.json({ error: { code: "internal_error", message: "Service unavailable.", details: [] } }, { status: 503 }),
      ),
    );
    renderAt("/demand?tab=trends");
    expect(await screen.findByText("Couldn't load demand trends")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Retry" })).toBeInTheDocument();
  });

  it("shows an empty state when the API returns no points", async () => {
    server.use(
      http.get(`${API_BASE_URL}/api/v1/sales/trends`, () =>
        HttpResponse.json(envelope({ atc_class: null, grain: "daily", start_date: "2019-01-01", end_date: "2019-01-01", points: [] })),
      ),
    );
    renderAt("/demand?tab=trends");
    expect(await screen.findByText("No demand data for this selection")).toBeInTheDocument();
  });

  it("re-queries the API with the selected ATC class", async () => {
    server.use(
      http.get(`${API_BASE_URL}/api/v1/sales/trends`, ({ request }) => {
        const url = new URL(request.url);
        const atcClass = url.searchParams.get("atc_class");
        return HttpResponse.json(
          envelope({
            atc_class: atcClass,
            grain: "daily",
            start_date: "2019-10-06",
            end_date: "2019-10-08",
            points: atcClass === "R03" ? [{ period: "2019-10-08", units_sold: 999.9 }] : [{ period: "2019-10-08", units_sold: 55.9 }],
          }),
        );
      }),
    );
    renderAt("/demand?tab=trends");
    // Single point per class -> average === peak === that point's
    // value, rendered in the derived-summary MetricCard.
    expect(await screen.findByText("55.9")).toBeInTheDocument();
    expect(screen.getByText("All classes")).toBeInTheDocument();

    await userEvent.selectOptions(screen.getByLabelText("ATC class"), "R03");
    expect(await screen.findByText("999.9")).toBeInTheDocument();
    expect(screen.getAllByText("R03").length).toBeGreaterThan(0); // the ATC Class summary card now reads R03
  });
});

describe("DemandIntelligencePage — ATC Analysis tab", () => {
  it("renders the ATC comparison table with real API fields", async () => {
    renderAt("/demand?tab=atc");
    const table = await screen.findByRole("table");
    expect(within(table).getByText("N02BE")).toBeInTheDocument();
    expect(within(table).getByText("49.4%")).toBeInTheDocument();
  });

  it("renders trend classifications via the shared domain-label mapping", async () => {
    renderAt("/demand?tab=atc");
    const table = await screen.findByRole("table");
    expect(within(table).getByText("Growing")).toBeInTheDocument();
    expect(within(table).getByText("No significant trend")).toBeInTheDocument();
  });

  it("renders concentration context (CR3, HHI) verbatim from the API", async () => {
    renderAt("/demand?tab=atc");
    expect(await screen.findByText("73.1%")).toBeInTheDocument();
    expect(screen.getByText("2909.9")).toBeInTheDocument();
  });
});

describe("DemandIntelligencePage — Seasonality tab", () => {
  it("renders seasonal strength values from the API", async () => {
    renderAt("/demand?tab=seasonality");
    expect(await screen.findByText("0.234")).toBeInTheDocument();
    expect(screen.getByText("0.553")).toBeInTheDocument();
  });

  it("renders an honest unavailable state with the API's reason when a metric can't be computed", async () => {
    server.use(
      http.get(`${API_BASE_URL}/api/v1/analytics/seasonality`, () =>
        HttpResponse.json(
          envelope({
            atc_class: "N05C",
            day_of_week_effect: {
              h_statistic: null,
              p_value: null,
              significant: null,
              mean_units_by_weekday: null,
              available: false,
              reason: "Insufficient non-zero observations for this ATC class.",
            },
            hour_of_day_effect: {
              h_statistic: null,
              p_value: null,
              significant: null,
              mean_units_by_hour: null,
              available: false,
              reason: "Insufficient non-zero observations for this ATC class.",
            },
            weekly_seasonal_strength: { strength: null, cycle_period: null, n_periods: null, interpretation: null, available: false, reason: "Fewer than 2 full cycles available." },
            annual_seasonal_strength: { strength: null, cycle_period: null, n_periods: null, interpretation: null, available: false, reason: "Fewer than 2 full cycles available." },
          }),
        ),
      ),
    );
    renderAt("/demand?tab=seasonality");
    expect((await screen.findAllByText("Not available")).length).toBeGreaterThan(0);
    expect(screen.getAllByText("Insufficient non-zero observations for this ATC class.").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Fewer than 2 full cycles available.").length).toBeGreaterThan(0);
  });
});

describe("DemandIntelligencePage — Anomalies tab", () => {
  it("renders anomaly results from the API", async () => {
    renderAt("/demand?tab=anomalies");
    expect(await screen.findByText("2")).toBeInTheDocument(); // total_count
    const table = await screen.findByRole("table");
    expect(within(table).getByText("N05C")).toBeInTheDocument();
    expect(within(table).getAllByText("High").length).toBeGreaterThan(0);
  });

  it("shows an empty state (not an error) when zero anomalies are found", async () => {
    server.use(
      http.get(`${API_BASE_URL}/api/v1/analytics/anomalies`, () =>
        HttpResponse.json(envelope({ atc_class: null, method: "rolling_zscore", total_count: 0, anomalies: [] })),
      ),
    );
    renderAt("/demand?tab=anomalies");
    expect(await screen.findByText("No anomalies for this selection")).toBeInTheDocument();
  });
});

describe("DemandIntelligencePage — hardcoded-value guard", () => {
  it("never hardcodes the M3/M7.1.5 headline numbers — every figure changes when the mocked API response changes", async () => {
    server.use(
      http.get(`${API_BASE_URL}/api/v1/analytics/atc`, () =>
        HttpResponse.json(
          envelope({
            classes: [
              {
                atc_class: "M01AB",
                total_demand: 1,
                average_daily_demand: 1,
                peak_daily_demand: 1,
                trough_daily_demand: 0,
                contribution_pct: 45.6,
                trend_slope: 0,
                trend_classification: "stable_or_no_significant_trend",
                trend_p_value: 0.9,
                volatility_cv: 0.1,
              },
            ],
            dominant_classes: ["M01AB"],
            concentration: {
              ranked: [{ atc_code: "M01AB", share_pct: 45.6, cumulative_share_pct: 45.6 }],
              concentration_ratio_top3_pct: 12.3,
              hhi: 555.5,
              hhi_scale_note: "0-10000 scale.",
            },
          }),
        ),
      ),
      http.get(`${API_BASE_URL}/api/v1/analytics/seasonality`, () =>
        HttpResponse.json(
          envelope({
            atc_class: "ALL",
            day_of_week_effect: { h_statistic: null, p_value: null, significant: null, mean_units_by_weekday: null, available: false, reason: "n/a" },
            hour_of_day_effect: { h_statistic: null, p_value: null, significant: null, mean_units_by_hour: null, available: false, reason: "n/a" },
            weekly_seasonal_strength: { strength: 0.777, cycle_period: 7, n_periods: 100, interpretation: "x", available: true },
            annual_seasonal_strength: { strength: 0.111, cycle_period: 12, n_periods: 20, interpretation: "x", available: true },
          }),
        ),
      ),
    );

    renderAt("/demand?tab=atc");
    expect(await screen.findByText("12.3%")).toBeInTheDocument();
    expect(screen.getByText("555.5")).toBeInTheDocument();
    expect(screen.queryByText("73.1%")).not.toBeInTheDocument();
    expect(screen.queryByText("2909.9")).not.toBeInTheDocument();

    renderAt("/demand?tab=seasonality");
    expect(await screen.findByText("0.777")).toBeInTheDocument();
    expect(screen.getByText("0.111")).toBeInTheDocument();
    expect(screen.queryByText("0.234")).not.toBeInTheDocument();
    expect(screen.queryByText("0.553")).not.toBeInTheDocument();
  });
});

describe("DemandIntelligencePage — URL state", () => {
  it("clicking a tab updates the URL query param", async () => {
    renderAt("/demand?tab=trends");
    await userEvent.click(screen.getByRole("tab", { name: "ATC Analysis" }));
    expect(await screen.findByRole("tab", { name: "ATC Analysis", selected: true })).toBeInTheDocument();
  });

  it("preserves tab state across browser back/forward navigation", async () => {
    const queryClient = createTestQueryClient();
    const router = createMemoryRouter(
      [{ path: "/demand", element: <DemandIntelligencePage /> }],
      { initialEntries: ["/demand?tab=trends", "/demand?tab=atc"], initialIndex: 1 },
    );

    render(
      <QueryClientProvider client={queryClient}>
        <RouterProvider router={router} />
      </QueryClientProvider>,
    );

    expect(screen.getByRole("tab", { name: "ATC Analysis", selected: true })).toBeInTheDocument();

    router.navigate(-1);
    await waitFor(() => expect(screen.getByRole("tab", { name: "Trends", selected: true })).toBeInTheDocument());

    router.navigate(1);
    await waitFor(() => expect(screen.getByRole("tab", { name: "ATC Analysis", selected: true })).toBeInTheDocument());
  });
});
