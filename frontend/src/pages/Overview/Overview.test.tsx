import { describe, expect, it } from "vitest";
import { screen, waitFor, within } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { server } from "../../mocks/server";
import { renderWithProviders } from "../../test/testUtils";
import { OverviewPage } from "./index";

const API_BASE_URL = "http://localhost:8000";

function envelope<T>(data: T) {
  return { data, metadata: { generated_at: new Date().toISOString(), source: "test-fixture" } };
}

describe("OverviewPage", () => {
  it("renders KPI data from the API", async () => {
    renderWithProviders(<OverviewPage />);
    expect(await screen.findByText("127,596")).toBeInTheDocument(); // total_demand: 127595.5, rounded
    expect(screen.getByText("60.6")).toBeInTheDocument(); // average_daily_demand: 60.59
    expect(screen.getByText("199.0")).toBeInTheDocument(); // peak_daily_demand: 198.95
  });

  it("renders the dominant ATC class and its share of total demand", async () => {
    renderWithProviders(<OverviewPage />);
    // Appears in both the KPI card and the Demand Position narrative.
    expect((await screen.findAllByText("N02BE")).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/49\.4%/).length).toBeGreaterThan(0);
  });

  it("renders concentration data — CR3, HHI, and the ranked table", async () => {
    renderWithProviders(<OverviewPage />);
    expect(await screen.findByText("73.1%")).toBeInTheDocument(); // concentration_ratio_top3_pct
    expect(screen.getByText("2909.9")).toBeInTheDocument(); // hhi
    // Scoped by accessible name (the Table component's own caption) —
    // the page now has more than one <table> (the Supply Planning
    // preview added its own scenario table in M7.9), so an unscoped
    // getByRole("table") is ambiguous.
    const table = screen.getByRole("table", { name: /Ranked ATC classes/ });
    expect(within(table).getByText("N02BE")).toBeInTheDocument();
    expect(within(table).getAllByText("49.4%").length).toBeGreaterThan(0); // share and cumulative share both 49.4% for the top row
  });

  it("renders trend signals for a statistically significant growing class", async () => {
    renderWithProviders(<OverviewPage />);
    // R03 is both the significant-growth signal and (in this fixture)
    // the highest-volatility class, so it legitimately appears twice.
    expect((await screen.findAllByText("R03")).length).toBeGreaterThan(0);
    expect(screen.getByText("Growing")).toBeInTheDocument();
  });

  it("renders trend signals for a statistically significant declining class", async () => {
    server.use(
      http.get(`${API_BASE_URL}/api/v1/analytics/atc`, () =>
        HttpResponse.json(
          envelope({
            classes: [
              {
                atc_class: "N02BA",
                total_demand: 5000,
                average_daily_demand: 2.4,
                peak_daily_demand: 10,
                trough_daily_demand: 0,
                contribution_pct: 4.0,
                trend_slope: -3.2,
                trend_classification: "declining",
                trend_p_value: 0.02,
                volatility_cv: 0.9,
              },
            ],
            dominant_classes: ["N02BA"],
            concentration: {
              ranked: [{ atc_code: "N02BA", share_pct: 100, cumulative_share_pct: 100 }],
              concentration_ratio_top3_pct: 100,
              hhi: 10000,
              hhi_scale_note: "0-10000 scale.",
            },
          }),
        ),
      ),
    );
    renderWithProviders(<OverviewPage />);
    expect(await screen.findByText("Declining")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /statistically significant decline/ })).toHaveAttribute(
      "href",
      "/forecast/N02BA",
    );
  });

  it("renders the data-quality warning and never hides it", async () => {
    renderWithProviders(<OverviewPage />);
    expect(await screen.findByText(/does not reconcile with the daily-grain sum/)).toBeInTheDocument();
    // Both the overall status and the Monthly reconciliation row are
    // "warn" in the fixture, so the short status badge legitimately
    // appears twice.
    expect(screen.getAllByText("WARN").length).toBeGreaterThan(0);
    expect(screen.getByText("Known source inconsistency")).toBeInTheDocument();
  });

  it("shows loading skeletons before data arrives", () => {
    renderWithProviders(<OverviewPage />);
    expect(screen.getAllByRole("status", { name: "Loading" }).length).toBeGreaterThan(0);
  });

  it("shows an error state for a failed section without blanking sections that succeeded", async () => {
    server.use(
      http.get(`${API_BASE_URL}/api/v1/kpis/summary`, () => HttpResponse.json({ error: { code: "internal_error", message: "Service unavailable.", details: [] } }, { status: 503 })),
    );
    renderWithProviders(<OverviewPage />);

    // Both the KPI row and the Demand Position section depend on
    // kpiQuery, so both legitimately show their own ErrorState.
    expect((await screen.findAllByText("This service is temporarily unavailable. Please try again shortly.")).length).toBeGreaterThan(0);
    expect(screen.getAllByRole("button", { name: "Retry" }).length).toBeGreaterThan(0);

    // Concentration (a different endpoint) still renders.
    expect(await screen.findByText("73.1%")).toBeInTheDocument();
  });

  it("shows an empty state when the API returns no ATC classes", async () => {
    server.use(
      http.get(`${API_BASE_URL}/api/v1/analytics/atc`, () =>
        HttpResponse.json(
          envelope({
            classes: [],
            dominant_classes: [],
            concentration: { ranked: [], concentration_ratio_top3_pct: null, hhi: null, hhi_scale_note: "0-10000 scale." },
          }),
        ),
      ),
    );
    renderWithProviders(<OverviewPage />);
    expect(await screen.findByText("No concentration data available")).toBeInTheDocument();
    expect(screen.getByText("No ATC class data available")).toBeInTheDocument();
  });

  it("shows a distinct empty state when ATC classes exist but none show a significant trend or volatility", async () => {
    server.use(
      http.get(`${API_BASE_URL}/api/v1/analytics/atc`, () =>
        HttpResponse.json(
          envelope({
            classes: [
              {
                atc_class: "M01AB",
                total_demand: 1000,
                average_daily_demand: 1,
                peak_daily_demand: 5,
                trough_daily_demand: 0,
                contribution_pct: 1.0,
                trend_slope: 0.1,
                trend_classification: "stable_or_no_significant_trend",
                trend_p_value: 0.8,
                volatility_cv: null,
              },
            ],
            dominant_classes: ["M01AB"],
            concentration: {
              ranked: [{ atc_code: "M01AB", share_pct: 100, cumulative_share_pct: 100 }],
              concentration_ratio_top3_pct: 100,
              hhi: 10000,
              hhi_scale_note: "0-10000 scale.",
            },
          }),
        ),
      ),
    );
    renderWithProviders(<OverviewPage />);
    expect(await screen.findByText("No significant signals detected")).toBeInTheDocument();
  });

  it("links to Demand Intelligence to investigate the dominant ATC class", async () => {
    renderWithProviders(<OverviewPage />);
    // /demand/atc/:atcClass is an orphaned M7.2 scaffold that was never
    // implemented (M7.5 shipped a shared ?tab=atc view instead) — this
    // link must point at the real Demand Intelligence tab, not the dead
    // placeholder route.
    const link = await screen.findByRole("link", { name: /Investigate N02BE exposure/ });
    expect(link).toHaveAttribute("href", "/demand?tab=atc");
  });

  it("links to the full Data Quality report", async () => {
    renderWithProviders(<OverviewPage />);
    const link = await screen.findByRole("link", { name: "View full report →" });
    expect(link).toHaveAttribute("href", "/data-quality");
  });

  it("links to Forecasting and Supply Planning", async () => {
    renderWithProviders(<OverviewPage />);
    expect(await screen.findByRole("link", { name: "Review 14-day demand forecasts" })).toHaveAttribute(
      "href",
      "/forecast",
    );
    expect(screen.getByRole("link", { name: "Review supply-planning scenarios" })).toHaveAttribute("href", "/planning");
  });

  it("never renders a hardcoded business value that bypasses the API — every KPI figure resolves only after the fetch", async () => {
    renderWithProviders(<OverviewPage />);
    // Immediately after render (before MSW resolves), the real value must
    // not yet be present — proving it came from the awaited response, not
    // a constant baked into the component.
    expect(screen.queryByText("127,596")).not.toBeInTheDocument();
    await waitFor(() => expect(screen.getByText("127,596")).toBeInTheDocument());
  });
});

describe("OverviewPage — Forecast preview (M7.9)", () => {
  it("renders the aggregate forecast's next-day value, WAPE, and model from the API", async () => {
    renderWithProviders(<OverviewPage />);
    expect(await screen.findByText("64.7")).toBeInTheDocument(); // forecast[0].prediction
    expect(screen.getByText("16.3%")).toBeInTheDocument(); // metrics.wape, 1 decimal
    expect(screen.getByText("ets")).toBeInTheDocument(); // model
    expect(screen.getByText(/Interval 35\.0–94\.4/)).toBeInTheDocument(); // lower/upper
  });

  it("links to the Forecasting page", async () => {
    renderWithProviders(<OverviewPage />);
    expect(await screen.findByRole("link", { name: "View forecasts →" })).toHaveAttribute("href", "/forecast");
  });

  it("shows an error state for a failed forecast fetch without blanking unrelated sections", async () => {
    server.use(
      http.get(`${API_BASE_URL}/api/v1/forecast/aggregate`, () =>
        HttpResponse.json({ error: { code: "internal_error", message: "Service unavailable.", details: [] } }, { status: 503 }),
      ),
    );
    renderWithProviders(<OverviewPage />);
    expect(await screen.findByText("Couldn't load the forecast")).toBeInTheDocument();
    // Concentration (a different endpoint) still renders.
    expect(await screen.findByText("73.1%")).toBeInTheDocument();
  });

  it("shows an empty state when the API returns no forecast points", async () => {
    server.use(
      http.get(`${API_BASE_URL}/api/v1/forecast/aggregate`, () =>
        HttpResponse.json(
          envelope({ atc_class: "ALL", horizon_days: 14, model: "ets", uncertainty_method: "ets_native_prediction_interval", forecast: [], metrics: { mae: null, rmse: null, wape: null, mase: null } }),
        ),
      ),
    );
    renderWithProviders(<OverviewPage />);
    expect(await screen.findByText("No forecast available")).toBeInTheDocument();
  });
});

describe("OverviewPage — Supply Planning preview (M7.9)", () => {
  it("renders real scenario definitions from the API — never a fabricated allocation/improvement figure", async () => {
    renderWithProviders(<OverviewPage />);
    expect(await screen.findByText("Balanced")).toBeInTheDocument();
    expect(screen.getByText("Conservative")).toBeInTheDocument();
    expect(screen.getByText("Lean")).toBeInTheDocument();
    expect(screen.getByText("95%")).toBeInTheDocument(); // balanced service_level_target: 0.95
    // The section is explicit that these are definitions, not a result —
    // it names "improvement"/"capacity budget" only to say those figures
    // don't exist here, so the right check is that this exact disclaimer
    // renders, not a blanket "the word never appears" check (which would
    // fail against the section's own honest copy).
    expect(
      screen.getByText(/only exist after running a scenario on the Supply Planning page/),
    ).toBeInTheDocument();
  });

  it("links to the Supply Planning page", async () => {
    renderWithProviders(<OverviewPage />);
    expect(await screen.findByRole("link", { name: "Open Supply Planning →" })).toHaveAttribute("href", "/planning");
  });

  it("shows an error state for a failed scenarios fetch without blanking unrelated sections", async () => {
    server.use(
      http.get(`${API_BASE_URL}/api/v1/optimization/scenarios`, () =>
        HttpResponse.json({ error: { code: "internal_error", message: "Service unavailable.", details: [] } }, { status: 503 }),
      ),
    );
    renderWithProviders(<OverviewPage />);
    expect(await screen.findByText("Couldn't load planning scenarios")).toBeInTheDocument();
    expect(await screen.findByText("73.1%")).toBeInTheDocument();
  });

  it("shows an empty state when the API returns no scenarios", async () => {
    server.use(
      http.get(`${API_BASE_URL}/api/v1/optimization/scenarios`, () => HttpResponse.json(envelope({ scenarios: [] }))),
    );
    renderWithProviders(<OverviewPage />);
    expect(await screen.findByText("No planning scenarios available")).toBeInTheDocument();
  });
});

describe("OverviewPage — Recommendations preview (M7.9)", () => {
  it("renders the total count, confidence tally, and a featured recommendation from the API", async () => {
    renderWithProviders(<OverviewPage />);
    expect(await screen.findByText("Treat N02BE as high planning exposure.")).toBeInTheDocument();
    expect(screen.getByText("Medium confidence")).toBeInTheDocument();
    expect(screen.getByText("Total Recommendations")).toBeInTheDocument();
    // Fixture has exactly 1 recommendation, "medium" confidence — the
    // total and low-confidence tallies must reflect that, not a guess.
    const totalCard = screen.getByText("Total Recommendations").closest("div");
    expect(totalCard?.parentElement).toHaveTextContent("1");
  });

  it("links to the Recommendations page", async () => {
    renderWithProviders(<OverviewPage />);
    expect(await screen.findByRole("link", { name: "View all recommendations →" })).toHaveAttribute(
      "href",
      "/recommendations",
    );
  });

  it("shows an error state for a failed recommendations fetch without blanking unrelated sections", async () => {
    server.use(
      http.get(`${API_BASE_URL}/api/v1/recommendations`, () =>
        HttpResponse.json({ error: { code: "internal_error", message: "Service unavailable.", details: [] } }, { status: 503 }),
      ),
    );
    renderWithProviders(<OverviewPage />);
    expect(await screen.findByText("Couldn't load recommendations")).toBeInTheDocument();
    expect(await screen.findByText("73.1%")).toBeInTheDocument();
  });

  it("shows an empty state when the API returns no recommendations", async () => {
    server.use(
      http.get(`${API_BASE_URL}/api/v1/recommendations`, () =>
        HttpResponse.json(envelope({ scenario: "balanced", recommendations: [] })),
      ),
    );
    renderWithProviders(<OverviewPage />);
    expect(await screen.findByText("No recommendations available")).toBeInTheDocument();
  });

  it("surfaces the lowest-confidence recommendation as the featured preview, not just the first in order", async () => {
    server.use(
      http.get(`${API_BASE_URL}/api/v1/recommendations`, () =>
        HttpResponse.json(
          envelope({
            scenario: "balanced",
            recommendations: [
              {
                atc_class: "M01AB",
                recommendation: "Standard balanced scenario policy applies for M01AB.",
                evidence: ["Evidence for M01AB."],
                assumptions: ["Assumption."],
                expected_effect: "Effect.",
                confidence: "medium-high",
                limitations: ["Limitation."],
              },
              {
                atc_class: "N05C",
                recommendation: "N05C's high CV does not, by itself, justify large safety stock.",
                evidence: ["Evidence for N05C."],
                assumptions: ["Assumption."],
                expected_effect: "Effect.",
                confidence: "low",
                limitations: ["Limitation."],
              },
            ],
          }),
        ),
      ),
    );
    renderWithProviders(<OverviewPage />);
    expect(await screen.findByText(/N05C's high CV does not/)).toBeInTheDocument();
    expect(screen.queryByText(/Standard balanced scenario policy applies for M01AB/)).not.toBeInTheDocument();
  });

  it("adds a Next Actions item for low-confidence recommendations only when at least one exists", async () => {
    server.use(
      http.get(`${API_BASE_URL}/api/v1/recommendations`, () =>
        HttpResponse.json(
          envelope({
            scenario: "balanced",
            recommendations: [
              {
                atc_class: "N05C",
                recommendation: "N05C's high CV does not, by itself, justify large safety stock.",
                evidence: ["Evidence."],
                assumptions: ["Assumption."],
                expected_effect: "Effect.",
                confidence: "low",
                limitations: ["Limitation."],
              },
            ],
          }),
        ),
      ),
    );
    renderWithProviders(<OverviewPage />);
    const link = await screen.findByRole("link", { name: /Review 1 low-confidence recommendation/ });
    expect(link).toHaveAttribute("href", "/recommendations");
  });
});

describe("OverviewPage — accessibility (M7.9)", () => {
  it("has exactly one h1 and gives every new preview section its own labelled landmark", async () => {
    renderWithProviders(<OverviewPage />);
    expect(await screen.findByRole("heading", { level: 1, name: "Executive Overview" })).toBeInTheDocument();
    expect(screen.getAllByRole("heading", { level: 1 })).toHaveLength(1);
    expect(screen.getByRole("heading", { level: 2, name: "Forecasting Intelligence" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { level: 2, name: "Supply Planning & Optimization" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { level: 2, name: "Recommendations Intelligence" })).toBeInTheDocument();
  });

  it("every drill-down link has a descriptive accessible name, not generic text", async () => {
    renderWithProviders(<OverviewPage />);
    // No link on the page should be an unlabelled "click here" / "more" —
    // every new preview action names its own destination.
    expect(await screen.findByRole("link", { name: "View forecasts →" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Open Supply Planning →" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "View all recommendations →" })).toBeInTheDocument();
  });
});
