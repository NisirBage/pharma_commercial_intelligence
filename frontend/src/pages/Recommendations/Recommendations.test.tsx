import { describe, expect, it } from "vitest";
import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { server } from "../../mocks/server";
import { renderWithProviders } from "../../test/testUtils";
import { RecommendationsPage } from "./index";

const API_BASE_URL = "http://localhost:8000";

function envelope<T>(data: T) {
  return { data, metadata: { generated_at: new Date().toISOString(), source: "test-fixture" } };
}

function renderPage() {
  return renderWithProviders(<RecommendationsPage />);
}

const RICH_FIXTURE = {
  scenario: "balanced",
  recommendations: [
    {
      atc_class: "R06",
      recommendation: "Standard balanced scenario policy applies — no special-case evidence identified for R06.",
      evidence: ["Selected model is the simple baseline 'moving_average_14' — M4 found no candidate meaningfully improved on it (validation WAPE 41.2%)."],
      assumptions: ["lead_time_days and service_level_target are scenario assumptions, not observed values from the Kaggle dataset."],
      expected_effect: "Reorder point and safety stock as calculated for this scenario.",
      confidence: "medium",
      limitations: ["The Kaggle dataset contains no real inventory, cost, or supplier data — this recommendation is a scenario simulation, not a real-world business commitment."],
    },
    {
      atc_class: "N05C",
      recommendation: "N05C's high CV does not, by itself, justify large safety stock — the absolute unit exposure (1.44 units) is what matters operationally.",
      evidence: [
        "Selected model is 'naive' with validation WAPE 100.0% (M4) — among the least reliable forecasts in the lineup.",
        "N05C has the highest historical CV of any class (M3: 1.84) but only ~1% of total demand.",
        "Absolute safety-stock requirement under this scenario is 1.44 units — evaluated on its own merits, not inferred from CV alone.",
      ],
      assumptions: ["lead_time_days and service_level_target are scenario assumptions, not observed values from the Kaggle dataset."],
      expected_effect: "Low absolute inventory exposure under any scenario, because absolute volume is small.",
      confidence: "low",
      limitations: [
        "The Kaggle dataset contains no real inventory, cost, or supplier data — this recommendation is a scenario simulation, not a real-world business commitment.",
        "M4 found N05C essentially unforecastable with current methods (test WAPE 100%) — treat its point forecast as low-confidence.",
      ],
    },
    {
      atc_class: "N02BE",
      recommendation: "Treat N02BE as high PLANNING EXPOSURE — errors here have the largest absolute impact because of its volume — not as 'high risk.'",
      evidence: [
        "Selected model 'moving_average_14' demonstrated a measurable improvement over baseline in M4 backtesting (validation WAPE 25.1%).",
        "N02BE represents ~49.4% of total observed demand (M3).",
      ],
      assumptions: ["lead_time_days and service_level_target are scenario assumptions, not observed values from the Kaggle dataset."],
      expected_effect: "A given percentage forecast error in N02BE translates to a larger absolute unit shortfall than the same percentage error in any other class.",
      confidence: "medium-high",
      limitations: ["The Kaggle dataset contains no real inventory, cost, or supplier data — this recommendation is a scenario simulation, not a real-world business commitment."],
    },
  ],
};

describe("RecommendationsPage — loading/error/empty", () => {
  it("shows a loading state before data arrives", () => {
    renderPage();
    expect(screen.getAllByRole("status", { name: "Loading" }).length).toBeGreaterThan(0);
  });

  it("shows an error state with retry on API failure — never a false empty state", async () => {
    server.use(
      http.get(`${API_BASE_URL}/api/v1/recommendations`, () =>
        HttpResponse.json({ error: { code: "internal_error", message: "Service unavailable.", details: [] } }, { status: 503 }),
      ),
    );
    renderPage();
    expect(await screen.findByText("Couldn't load recommendations")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Retry" })).toBeInTheDocument();
    expect(screen.queryByText("No recommendations available")).not.toBeInTheDocument();
  });

  it("shows a true empty state when the API returns zero recommendations", async () => {
    server.use(
      http.get(`${API_BASE_URL}/api/v1/recommendations`, () => HttpResponse.json(envelope({ scenario: "balanced", recommendations: [] }))),
    );
    renderPage();
    expect(await screen.findByText("No recommendations available")).toBeInTheDocument();
  });
});

describe("RecommendationsPage — recommendation content", () => {
  it("renders the recommendation text, expected effect, and ATC class for each item", async () => {
    server.use(http.get(`${API_BASE_URL}/api/v1/recommendations`, () => HttpResponse.json(envelope(RICH_FIXTURE))));
    renderPage();
    expect(await screen.findByText("N02BE")).toBeInTheDocument();
    expect(screen.getByText(/Treat N02BE as high PLANNING EXPOSURE/)).toBeInTheDocument();
    expect(screen.getByText("A given percentage forecast error in N02BE translates to a larger absolute unit shortfall than the same percentage error in any other class.")).toBeInTheDocument();
  });

  it("renders confidence as a categorical label, never a number", async () => {
    server.use(http.get(`${API_BASE_URL}/api/v1/recommendations`, () => HttpResponse.json(envelope(RICH_FIXTURE))));
    renderPage();
    // Confidence renders as exactly one of these 3 categorical labels —
    // never a fabricated percentage/fraction for a value the API never
    // expressed numerically. (Evidence text separately and legitimately
    // contains real "%" figures from M3/M4 findings — e.g. "validation
    // WAPE 41.2%" — so the check is scoped to the confidence label
    // itself, not "no % anywhere on the page".)
    const low = await screen.findByText("Low confidence");
    const medium = screen.getByText("Medium confidence");
    const mediumHigh = screen.getByText("Medium-high confidence");
    for (const badge of [low, medium, mediumHigh]) {
      expect(badge.textContent).not.toMatch(/[%\d]/);
    }
  });

  it("renders evidence visibly, without requiring interaction", async () => {
    server.use(http.get(`${API_BASE_URL}/api/v1/recommendations`, () => HttpResponse.json(envelope(RICH_FIXTURE))));
    renderPage();
    expect(await screen.findByText(/N02BE represents ~49\.4% of total observed demand/)).toBeInTheDocument();
  });

  it("renders limitations visibly, including class-specific ones", async () => {
    server.use(http.get(`${API_BASE_URL}/api/v1/recommendations`, () => HttpResponse.json(envelope(RICH_FIXTURE))));
    renderPage();
    expect(await screen.findByText(/M4 found N05C essentially unforecastable/)).toBeInTheDocument();
  });

  it("puts assumptions behind a keyboard-accessible disclosure", async () => {
    server.use(http.get(`${API_BASE_URL}/api/v1/recommendations`, () => HttpResponse.json(envelope(RICH_FIXTURE))));
    renderPage();
    await screen.findByText("N02BE");
    const summaries = screen.getAllByText("Assumptions");
    expect(summaries.length).toBeGreaterThan(0);
    // All 3 fixture items share byte-identical assumptions text, so text
    // queries can't distinguish which card's bullet is which — the real
    // mechanism under test is the <details> element's own `open` state
    // (what a real browser also uses to decide visibility; jsdom doesn't
    // implement native <details> closed-content hiding via CSS, so
    // asserting on rendered text presence/absence isn't reliable here).
    const details = summaries[0]!.closest("details");
    expect(details).not.toBeNull();
    expect(details?.open).toBe(false);

    await userEvent.click(summaries[0]!);

    expect(details?.open).toBe(true);
    // With the first card's <details> open, its assumption text is now
    // findable via keyboard-triggered disclosure (Space/Enter on a
    // native <summary> toggles the same `open` property userEvent.click
    // exercises here).
    expect(within(details!).getByText(/not observed values from the Kaggle dataset/)).toBeInTheDocument();
  });
});

describe("RecommendationsPage — ordering", () => {
  it("preserves the API's own order — never silently re-sorted", async () => {
    server.use(http.get(`${API_BASE_URL}/api/v1/recommendations`, () => HttpResponse.json(envelope(RICH_FIXTURE))));
    renderPage();
    const atcClasses = await screen.findAllByText(/^(R06|N05C|N02BE)$/);
    expect(atcClasses.map((el) => el.textContent)).toEqual(["R06", "N05C", "N02BE"]);
  });
});

describe("RecommendationsPage — filtering", () => {
  it("filters the displayed list by confidence without changing the total-recommendations count", async () => {
    server.use(http.get(`${API_BASE_URL}/api/v1/recommendations`, () => HttpResponse.json(envelope(RICH_FIXTURE))));
    renderPage();
    await screen.findByText("N02BE");
    expect(screen.getByText("R06")).toBeInTheDocument();
    expect(screen.getByText("N05C")).toBeInTheDocument();

    await userEvent.selectOptions(screen.getByLabelText("Filter by confidence"), "low");

    expect(screen.getByText("N05C")).toBeInTheDocument();
    expect(screen.queryByText("R06")).not.toBeInTheDocument();
    expect(screen.queryByText("N02BE")).not.toBeInTheDocument();
    // The summary KPI still reflects the full, unfiltered API response
    // (3 total), not the filtered subset (1 item) — proving the filter
    // never mutates the underlying data the summary is computed from.
    expect(screen.getByText("3")).toBeInTheDocument();
  });

  it("shows a distinct empty state when a filter matches nothing, not the true-empty message", async () => {
    server.use(
      http.get(`${API_BASE_URL}/api/v1/recommendations`, () =>
        HttpResponse.json(envelope({ scenario: "balanced", recommendations: [RICH_FIXTURE.recommendations[0]!] })),
      ),
    );
    renderPage();
    await screen.findByText("R06");
    await userEvent.selectOptions(screen.getByLabelText("Filter by confidence"), "low");
    expect(await screen.findByText("No recommendations match this filter")).toBeInTheDocument();
    expect(screen.queryByText("No recommendations available")).not.toBeInTheDocument();
  });

  it("resets to the full list when 'All confidence levels' is selected again", async () => {
    server.use(http.get(`${API_BASE_URL}/api/v1/recommendations`, () => HttpResponse.json(envelope(RICH_FIXTURE))));
    renderPage();
    await screen.findByText("N02BE");
    await userEvent.selectOptions(screen.getByLabelText("Filter by confidence"), "low");
    expect(screen.queryByText("R06")).not.toBeInTheDocument();
    await userEvent.selectOptions(screen.getByLabelText("Filter by confidence"), "");
    expect(screen.getByText("R06")).toBeInTheDocument();
    expect(screen.getByText("N05C")).toBeInTheDocument();
    expect(screen.getByText("N02BE")).toBeInTheDocument();
  });

  it("changing the scenario re-queries the API with the new scenario parameter", async () => {
    let lastScenarioParam: string | null = null;
    server.use(
      http.get(`${API_BASE_URL}/api/v1/recommendations`, ({ request }) => {
        lastScenarioParam = new URL(request.url).searchParams.get("scenario");
        return HttpResponse.json(envelope({ scenario: lastScenarioParam ?? "balanced", recommendations: [] }));
      }),
    );
    renderPage();
    await screen.findByLabelText("Planning scenario");
    await userEvent.selectOptions(screen.getByLabelText("Planning scenario"), "lean");
    await screen.findByText("No recommendations available");
    expect(lastScenarioParam).toBe("lean");
  });
});

describe("RecommendationsPage — hardcoded-value guard", () => {
  it("never hardcodes recommendation text — every value changes when the mocked API response changes", async () => {
    server.use(
      http.get(`${API_BASE_URL}/api/v1/recommendations`, () =>
        HttpResponse.json(
          envelope({
            scenario: "balanced",
            recommendations: [
              {
                atc_class: "M01AB",
                recommendation: "Completely custom test recommendation text that matches nothing in the real dataset.",
                evidence: ["Custom test evidence line."],
                assumptions: ["Custom test assumption line."],
                expected_effect: "Custom test expected effect.",
                confidence: "medium",
                limitations: ["Custom test limitation."],
              },
            ],
          }),
        ),
      ),
    );
    renderPage();
    expect(await screen.findByText("Completely custom test recommendation text that matches nothing in the real dataset.")).toBeInTheDocument();
    expect(screen.getByText("Custom test evidence line.")).toBeInTheDocument();
    expect(screen.getByText("Custom test limitation.")).toBeInTheDocument();
    expect(screen.queryByText(/Treat N02BE/)).not.toBeInTheDocument();
    expect(screen.queryByText(/high planning exposure/)).not.toBeInTheDocument();
  });
});

describe("RecommendationsPage — accessibility", () => {
  it("labels the scenario and confidence-filter controls", async () => {
    renderPage();
    expect(await screen.findByLabelText("Planning scenario")).toBeInTheDocument();
    expect(screen.getByLabelText("Filter by confidence")).toBeInTheDocument();
  });

  it("renders the page heading", () => {
    renderPage();
    expect(screen.getByRole("heading", { level: 1, name: "Recommendations Intelligence" })).toBeInTheDocument();
  });
});
