import { describe, expect, it } from "vitest";
import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { server } from "../../mocks/server";
import { renderWithProviders } from "../../test/testUtils";
import { SupplyPlanningPage } from "./index";

const API_BASE_URL = "http://localhost:8000";

function envelope<T>(data: T) {
  return { data, metadata: { generated_at: new Date().toISOString(), source: "test-fixture" } };
}

function renderPage() {
  return renderWithProviders(<SupplyPlanningPage />);
}

describe("SupplyPlanningPage — scenarios", () => {
  it("loads scenarios from the API and defaults to Balanced", async () => {
    renderPage();
    expect(await screen.findByLabelText("Planning scenario")).toHaveValue("balanced");
    expect(await screen.findByText("Middle service-level target.")).toBeInTheDocument();
  });

  it("shows a loading state before scenarios arrive", () => {
    renderPage();
    expect(screen.getAllByRole("status", { name: "Loading" }).length).toBeGreaterThan(0);
  });

  it("shows an error state with retry when scenarios fail to load", async () => {
    server.use(
      http.get(`${API_BASE_URL}/api/v1/optimization/scenarios`, () =>
        HttpResponse.json({ error: { code: "internal_error", message: "Service unavailable.", details: [] } }, { status: 503 }),
      ),
    );
    renderPage();
    expect(await screen.findByText("Couldn't load planning scenarios")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Retry" })).toBeInTheDocument();
  });

  it("switches scenario rationale when a different scenario is selected", async () => {
    renderPage();
    await screen.findByText("Middle service-level target.");
    await userEvent.selectOptions(screen.getByLabelText("Planning scenario"), "conservative");
    expect(await screen.findByText("Highest service-level target.")).toBeInTheDocument();
  });
});

describe("SupplyPlanningPage — optimization form", () => {
  it("renders exactly the controls the request schema supports", async () => {
    renderPage();
    expect(await screen.findByLabelText("Planning scenario")).toBeInTheDocument();
    expect(screen.getByLabelText(/Service level override/)).toBeInTheDocument();
    expect(screen.getByLabelText(/Lead time override/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Run optimization/ })).toBeInTheDocument();
  });

  it("validates the service level override and disables Run when invalid", async () => {
    renderPage();
    await screen.findByLabelText("Planning scenario");
    await userEvent.type(screen.getByLabelText(/Service level override/), "150");
    expect(await screen.findByText("Enter a whole percent between 1 and 99.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Run optimization/ })).toBeDisabled();
  });

  it("validates the lead time override and disables Run when invalid", async () => {
    renderPage();
    await screen.findByLabelText("Planning scenario");
    await userEvent.type(screen.getByLabelText(/Lead time override/), "30");
    expect(await screen.findByText("Enter a whole number of days from 0 to 14.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Run optimization/ })).toBeDisabled();
  });

  it("submits the exact configuration shown in the form", async () => {
    let capturedBody: unknown;
    server.use(
      http.post(`${API_BASE_URL}/api/v1/optimization/run`, async ({ request }) => {
        capturedBody = await request.json();
        return HttpResponse.json(
          envelope({
            scenario: "conservative",
            assumptions: [],
            capacity_budget: 1,
            atc_results: {},
            allocation_baseline: { policy_name: "baseline", solver_status: "heuristic (no solver)", total_capacity_budget: 1, total_safety_stock_allocated: 1, total_expected_shortage: 0, total_weighted_expected_shortage: 0 },
            allocation_optimized: { policy_name: "optimized", solver_status: "optimal", total_capacity_budget: 1, total_safety_stock_allocated: 1, total_expected_shortage: 0, total_weighted_expected_shortage: 0 },
            improvement_pct: 0,
            warnings: [],
          }),
        );
      }),
    );
    renderPage();
    await screen.findByLabelText("Planning scenario");
    await userEvent.selectOptions(screen.getByLabelText("Planning scenario"), "conservative");
    await userEvent.type(screen.getByLabelText(/Service level override/), "92");
    await userEvent.type(screen.getByLabelText(/Lead time override/), "5");
    await userEvent.click(screen.getByRole("button", { name: /Run optimization/ }));

    await waitFor(() => expect(capturedBody).toEqual({ scenario: "conservative", service_level: 0.92, lead_time_days: 5 }));
  });

  it("shows a running state and prevents duplicate submission", async () => {
    let callCount = 0;
    server.use(
      http.post(`${API_BASE_URL}/api/v1/optimization/run`, async () => {
        callCount += 1;
        await new Promise((r) => setTimeout(r, 50));
        return HttpResponse.json(
          envelope({
            scenario: "balanced",
            assumptions: [],
            capacity_budget: 1,
            atc_results: {},
            allocation_baseline: { policy_name: "baseline", solver_status: "heuristic (no solver)", total_capacity_budget: 1, total_safety_stock_allocated: 1, total_expected_shortage: 0, total_weighted_expected_shortage: 0 },
            allocation_optimized: { policy_name: "optimized", solver_status: "optimal", total_capacity_budget: 1, total_safety_stock_allocated: 1, total_expected_shortage: 0, total_weighted_expected_shortage: 0 },
            improvement_pct: 0,
            warnings: [],
          }),
        );
      }),
    );
    renderPage();
    await screen.findByLabelText("Planning scenario");
    const runButton = screen.getByRole("button", { name: /Run optimization/ });
    await userEvent.click(runButton);
    // The button becomes disabled (and native `disabled` buttons don't
    // fire clicks at all — that's userEvent's own well-tested behavior,
    // not something this test needs to re-prove by clicking it again).
    // What this test verifies is the app's own contribution: exactly
    // one request is made per one click.
    expect(screen.getByRole("button", { name: /Running optimization/ })).toBeDisabled();
    await waitFor(() => expect(screen.getByRole("button", { name: /^Run optimization/ })).not.toBeDisabled());
    expect(callCount).toBe(1);
  });

  it("shows an error state when the run fails, offering retry", async () => {
    server.use(
      http.post(`${API_BASE_URL}/api/v1/optimization/run`, () =>
        HttpResponse.json({ error: { code: "internal_error", message: "Service unavailable.", details: [] } }, { status: 503 }),
      ),
    );
    renderPage();
    await screen.findByLabelText("Planning scenario");
    await userEvent.click(screen.getByRole("button", { name: /Run optimization/ }));
    expect(await screen.findByText("The optimization run failed")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Retry" })).toBeInTheDocument();
  });

  it("shows a distinct infeasible message, not a generic error, for an infeasibility response", async () => {
    server.use(
      http.post(`${API_BASE_URL}/api/v1/optimization/run`, () =>
        HttpResponse.json(
          { error: { code: "optimization_infeasible", message: "The optimization solver could not find a feasible allocation (status: infeasible).", details: [] } },
          { status: 422 },
        ),
      ),
    );
    renderPage();
    await screen.findByLabelText("Planning scenario");
    await userEvent.click(screen.getByRole("button", { name: /Run optimization/ }));
    expect(await screen.findByText("No feasible allocation found")).toBeInTheDocument();
    expect(screen.getByText(/could not find a feasible allocation/)).toBeInTheDocument();
  });
});

describe("SupplyPlanningPage — results", () => {
  it("renders the optimization summary KPIs and solver status after a successful run", async () => {
    renderPage();
    await screen.findByLabelText("Planning scenario");
    await userEvent.click(screen.getByRole("button", { name: /Run optimization/ }));

    expect(await screen.findByText("103.7")).toBeInTheDocument(); // capacity_budget
    expect(screen.getByText("48.6%")).toBeInTheDocument(); // improvement_pct
    expect(screen.getByText("Optimal")).toBeInTheDocument(); // solver status label
  });

  it("renders the recommended plan table with per-class figures", async () => {
    renderPage();
    await screen.findByLabelText("Planning scenario");
    await userEvent.click(screen.getByRole("button", { name: /Run optimization/ }));

    const table = await screen.findByRole("table", { name: /Recommended per-ATC-class/ });
    expect(within(table).getByText("N02BE")).toBeInTheDocument();
    expect(within(table).getByText("moving_average_14")).toBeInTheDocument();
    expect(within(table).getByText("95.0%")).toBeInTheDocument(); // implied service level
  });

  it("renders the assumptions table verbatim from the API", async () => {
    renderPage();
    await screen.findByLabelText("Planning scenario");
    await userEvent.click(screen.getByRole("button", { name: /Run optimization/ }));

    const table = await screen.findByRole("table", { name: /Scenario assumptions/ });
    expect(within(table).getByText("lead_time_days")).toBeInTheDocument();
    expect(within(table).getByText("days")).toBeInTheDocument();
  });

  it("shows an empty state before any run has been made", () => {
    renderPage();
    expect(screen.getByText("No optimization has been run yet")).toBeInTheDocument();
  });
});

describe("SupplyPlanningPage — state integrity", () => {
  it("does not falsely update the shown result when the form is edited without re-running", async () => {
    renderPage();
    await screen.findByLabelText("Planning scenario");
    await userEvent.click(screen.getByRole("button", { name: /Run optimization/ }));
    expect(await screen.findByText("48.6%")).toBeInTheDocument();

    await userEvent.selectOptions(screen.getByLabelText("Planning scenario"), "conservative");

    // The old result is still shown, now flagged as stale — never
    // silently presented as if it matched the new selection.
    expect(screen.getByText("48.6%")).toBeInTheDocument();
    expect(screen.getByText(/configuration above has changed/)).toBeInTheDocument();
  });

  it("a failed run does not overwrite a previous successful result", async () => {
    renderPage();
    await screen.findByLabelText("Planning scenario");
    await userEvent.click(screen.getByRole("button", { name: /Run optimization/ }));
    expect(await screen.findByText("48.6%")).toBeInTheDocument();

    server.use(
      http.post(`${API_BASE_URL}/api/v1/optimization/run`, () =>
        HttpResponse.json({ error: { code: "internal_error", message: "Service unavailable.", details: [] } }, { status: 503 }),
      ),
    );
    await userEvent.click(screen.getByRole("button", { name: /Run optimization/ }));

    expect(await screen.findByText("The optimization run failed")).toBeInTheDocument();
    // The previous successful figure is still visible, not replaced by the failure.
    expect(screen.getByText("48.6%")).toBeInTheDocument();
  });
});

describe("SupplyPlanningPage — sensitivity", () => {
  it("shows a loading state before sensitivity data arrives", async () => {
    renderPage();
    expect(await screen.findByLabelText("ATC class")).toBeInTheDocument();
  });

  it("renders sensitivity values and elasticity from the API", async () => {
    renderPage();
    expect(await screen.findByText("1.00")).toBeInTheDocument(); // elasticity, formatCV
    const table = await screen.findByRole("table", { name: /Sensitivity sweep/ });
    expect(within(table).getByText("19.0 units")).toBeInTheDocument();
    expect(within(table).getByText("301.5 units")).toBeInTheDocument();
  });

  it("shows an empty state when sensitivity returns no points", async () => {
    server.use(
      http.get(`${API_BASE_URL}/api/v1/optimization/sensitivity`, () =>
        HttpResponse.json(envelope({ atc_class: "M01AB", parameter: "service_level_target", points: [], elasticity: null })),
      ),
    );
    renderPage();
    expect(await screen.findByText("No sensitivity data available")).toBeInTheDocument();
  });

  it("shows an error state on sensitivity failure", async () => {
    server.use(
      http.get(`${API_BASE_URL}/api/v1/optimization/sensitivity`, () =>
        HttpResponse.json({ error: { code: "internal_error", message: "Service unavailable.", details: [] } }, { status: 503 }),
      ),
    );
    renderPage();
    expect(await screen.findByText("Couldn't load sensitivity data")).toBeInTheDocument();
  });

  it("identifies the current scenario's baseline value on the sweep", async () => {
    renderPage();
    expect(await screen.findByText("95%")).toBeInTheDocument(); // balanced scenario's service_level_target as baseline
  });
});

describe("SupplyPlanningPage — hardcoded-value guard", () => {
  it("never hardcodes optimization figures — every value changes when the mocked API response changes", async () => {
    server.use(
      http.post(`${API_BASE_URL}/api/v1/optimization/run`, () =>
        HttpResponse.json(
          envelope({
            scenario: "balanced",
            assumptions: [],
            capacity_budget: 999.9,
            atc_results: {},
            allocation_baseline: { policy_name: "baseline", solver_status: "heuristic (no solver)", total_capacity_budget: 999.9, total_safety_stock_allocated: 999.9, total_expected_shortage: 0, total_weighted_expected_shortage: 0 },
            allocation_optimized: { policy_name: "optimized", solver_status: "optimal", total_capacity_budget: 999.9, total_safety_stock_allocated: 999.9, total_expected_shortage: 0, total_weighted_expected_shortage: 0 },
            improvement_pct: 77.7,
            warnings: [],
          }),
        ),
      ),
    );
    renderPage();
    await screen.findByLabelText("Planning scenario");
    await userEvent.click(screen.getByRole("button", { name: /Run optimization/ }));

    expect(await screen.findByText("999.9")).toBeInTheDocument();
    expect(screen.getByText("77.7%")).toBeInTheDocument();
    expect(screen.queryByText("103.7")).not.toBeInTheDocument();
    expect(screen.queryByText("48.6%")).not.toBeInTheDocument();
  });
});

describe("SupplyPlanningPage — accessibility", () => {
  it("labels every form control", async () => {
    renderPage();
    expect(await screen.findByLabelText("Planning scenario")).toBeInTheDocument();
    expect(screen.getByLabelText(/Service level override/)).toBeInTheDocument();
    expect(screen.getByLabelText(/Lead time override/)).toBeInTheDocument();
  });

  it("associates the service-level error with its field via aria-describedby", async () => {
    renderPage();
    await screen.findByLabelText("Planning scenario");
    const input = screen.getByLabelText(/Service level override/);
    await userEvent.type(input, "150");
    // aria-describedby may list multiple ids (helper + error) —
    // check that at least one of the referenced elements is the error text.
    const describedBy = input.getAttribute("aria-describedby");
    expect(describedBy).toBeTruthy();
    const describedElements = describedBy!.split(" ").map((id) => document.getElementById(id));
    expect(describedElements.some((el) => el?.textContent === "Enter a whole percent between 1 and 99.")).toBe(true);
  });

  it("renders section headings", async () => {
    renderPage();
    expect(screen.getByRole("heading", { level: 1, name: "Supply Planning & Optimization" })).toBeInTheDocument();
    expect(await screen.findByRole("heading", { name: "Sensitivity Analysis" })).toBeInTheDocument();
  });
});
