import { describe, expect, it } from "vitest";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { QueryClientProvider } from "@tanstack/react-query";
import { createMemoryRouter, RouterProvider } from "react-router-dom";
import { server } from "../../mocks/server";
import { createTestQueryClient } from "../../test/testUtils";
import { ForecastingPage } from "./index";

const API_BASE_URL = "http://localhost:8000";

function envelope<T>(data: T) {
  return { data, metadata: { generated_at: new Date().toISOString(), source: "test-fixture" } };
}

/**
 * Renders ForecastingPage behind BOTH real forecast routes so
 * `useParams()` actually resolves `:atcClass` — a bare MemoryRouter
 * (the shared `renderWithProviders` helper) has no `<Routes>` tree, so
 * it always returns `{}` from useParams() regardless of the URL
 * string passed to it. Every test in this file needs real route
 * matching (this is the first page whose behavior depends on a path
 * param, not just `useSearchParams`), so this local helper is used
 * throughout instead of the shared one.
 */
function renderForecast(initialEntries: string | string[], initialIndex?: number) {
  const entries = Array.isArray(initialEntries) ? initialEntries : [initialEntries];
  const queryClient = createTestQueryClient();
  const router = createMemoryRouter(
    [
      { path: "/forecast", element: <ForecastingPage /> },
      { path: "/forecast/:atcClass", element: <ForecastingPage /> },
    ],
    { initialEntries: entries, initialIndex: initialIndex ?? entries.length - 1 },
  );
  const result = render(
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  );
  return { ...result, router };
}

describe("ForecastingPage — routing", () => {
  it("defaults to the aggregate forecast at /forecast", async () => {
    renderForecast("/forecast");
    expect(await screen.findByText(/14-day horizon/)).toBeInTheDocument();
    expect(screen.getByText(/ · ets ·/)).toBeInTheDocument(); // aggregate fixture's model, in the chart subtitle
  });

  it("shows the per-class forecast at /forecast/N02BE", async () => {
    renderForecast("/forecast/N02BE");
    // "moving_average_14" legitimately appears twice — the chart's
    // subtitle (forecast model) and the diagnostics card's subtitle
    // (diagnostics model) — both correctly N02BE's model.
    expect((await screen.findAllByText(/moving_average_14/)).length).toBeGreaterThan(0);
    expect(screen.getByLabelText("ATC class")).toHaveValue("N02BE");
  });

  it("shows NotFoundPage for an unrecognized ATC class", () => {
    renderForecast("/forecast/NOT_A_REAL_CLASS");
    expect(screen.getByText(/is not a recognized ATC class/)).toBeInTheDocument();
  });

  it("navigating the ATC selector routes to the per-class forecast and re-queries", async () => {
    const { router } = renderForecast("/forecast");
    expect(await screen.findByText(/ · ets ·/)).toBeInTheDocument();

    await userEvent.selectOptions(screen.getByLabelText("ATC class"), "N02BE");
    await waitFor(() => expect(router.state.location.pathname).toBe("/forecast/N02BE"));
    expect((await screen.findAllByText(/moving_average_14/)).length).toBeGreaterThan(0);
  });

  it("preserves the selected class across browser back/forward", async () => {
    const { router } = renderForecast(["/forecast", "/forecast/N02BE"], 1);
    expect(await screen.findByLabelText("ATC class")).toHaveValue("N02BE");

    router.navigate(-1);
    await waitFor(() => expect(screen.getByLabelText("ATC class")).toHaveValue(""));
    expect(await screen.findByText(/ · ets ·/)).toBeInTheDocument();

    router.navigate(1);
    await waitFor(() => expect(screen.getByLabelText("ATC class")).toHaveValue("N02BE"));
  });
});

describe("ForecastingPage — forecast", () => {
  it("renders forecast data from the API", async () => {
    renderForecast("/forecast");
    expect(await screen.findByText(/14-day horizon/)).toBeInTheDocument();
  });

  it("shows a loading state before data arrives", () => {
    renderForecast("/forecast");
    expect(screen.getAllByRole("status", { name: "Loading" }).length).toBeGreaterThan(0);
  });

  it("shows an error state with retry on forecast failure", async () => {
    server.use(
      http.get(`${API_BASE_URL}/api/v1/forecast/aggregate`, () =>
        HttpResponse.json({ error: { code: "internal_error", message: "Service unavailable.", details: [] } }, { status: 503 }),
      ),
    );
    renderForecast("/forecast");
    expect(await screen.findByText("Couldn't load the forecast")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Retry" })).toBeInTheDocument();
  });

  it("retries the query when Retry is clicked", async () => {
    let calls = 0;
    server.use(
      http.get(`${API_BASE_URL}/api/v1/forecast/aggregate`, () => {
        calls += 1;
        if (calls === 1) {
          return HttpResponse.json({ error: { code: "internal_error", message: "Service unavailable.", details: [] } }, { status: 503 });
        }
        return HttpResponse.json(
          envelope({
            atc_class: "ALL",
            horizon_days: 14,
            model: "ets",
            uncertainty_method: "ets_native_prediction_interval",
            forecast: [{ date: "2019-10-09", prediction: 64.7, lower: 35.0, upper: 94.4 }],
            metrics: { mae: 11.46, rmse: 14.99, wape: 16.27, mase: 0.66 },
          }),
        );
      }),
    );
    renderForecast("/forecast");
    expect(await screen.findByText("Couldn't load the forecast")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Retry" }));
    expect(await screen.findByText(/14-day horizon/)).toBeInTheDocument();
    expect(calls).toBe(2);
  });

  it("shows an empty state when the forecast has no points", async () => {
    server.use(
      http.get(`${API_BASE_URL}/api/v1/forecast/aggregate`, () =>
        HttpResponse.json(
          envelope({
            atc_class: "ALL",
            horizon_days: 14,
            model: "ets",
            uncertainty_method: "ets_native_prediction_interval",
            forecast: [],
            metrics: { mae: null, rmse: null, wape: null, mase: null },
          }),
        ),
      ),
    );
    renderForecast("/forecast");
    expect(await screen.findByText("No forecast available")).toBeInTheDocument();
  });

  it("distinguishes historical from forecast rows in the accessible table", async () => {
    renderForecast("/forecast");
    const table = await screen.findByRole("table", { name: /Historical and forecast demand/ });
    // 3 historical rows (fixture) + 1 forecast row.
    expect(within(table).getAllByText("Historical").length).toBe(3);
    expect(within(table).getAllByText("Forecast").length).toBe(1);
  });

  it("renders the confidence interval when the API returns lower/upper bounds", async () => {
    renderForecast("/forecast");
    expect(await screen.findByText("Confidence interval")).toBeInTheDocument(); // legend item
    const table = await screen.findByRole("table", { name: /Historical and forecast demand/ });
    expect(within(table).getByText("35.0 – 94.4")).toBeInTheDocument();
  });

  it("renders derived overview metrics, clearly labeled as computed", async () => {
    renderForecast("/forecast");
    // 55.9/64.7 each appear twice — once in the MetricCard, once again
    // in the combined historical+forecast table's Observed/Prediction
    // column for that same underlying value.
    expect((await screen.findAllByText("55.9")).length).toBeGreaterThan(0); // latest historical
    expect(screen.getAllByText("64.7").length).toBeGreaterThan(0); // avg forecast (single point)
    expect(screen.getByText("15.7%")).toBeInTheDocument(); // expected change: (64.7-55.9)/55.9
    expect(screen.getByText(/computed from the points shown/)).toBeInTheDocument();
  });
});

describe("ForecastingPage — diagnostics", () => {
  it("renders diagnostics from the API", async () => {
    renderForecast("/forecast/N02BE");
    // 33.7% (WAPE) legitimately appears twice — once in the Overview
    // KPI row (headline glance) and once in the Diagnostics MetricCard
    // (full accuracy detail) — both from the same underlying fixture
    // value for N02BE.
    expect((await screen.findAllByText("33.7%")).length).toBeGreaterThan(0);
    expect(screen.getByText("84 backtest residuals", { exact: false })).toBeInTheDocument();
  });

  it("renders a meaningful autocorrelation status, not just a number", async () => {
    renderForecast("/forecast/N02BE");
    expect(await screen.findByText(/Autocorrelation detected/)).toBeInTheDocument();
  });

  it("shows an error state for a diagnostics failure without blanking the forecast chart", async () => {
    server.use(
      http.get(`${API_BASE_URL}/api/v1/forecast/:atcClass/diagnostics`, () =>
        HttpResponse.json({ error: { code: "internal_error", message: "Service unavailable.", details: [] } }, { status: 503 }),
      ),
    );
    renderForecast("/forecast/N02BE");
    expect(await screen.findByText("Couldn't load forecast diagnostics")).toBeInTheDocument();
    // The forecast chart (independent query) still renders.
    expect(await screen.findByText(/14-day horizon/)).toBeInTheDocument();
  });
});

describe("ForecastingPage — hardcoded-value guard", () => {
  it("never hardcodes forecast/diagnostic figures — every value changes when the mocked API response changes", async () => {
    server.use(
      http.get(`${API_BASE_URL}/api/v1/forecast/aggregate`, () =>
        HttpResponse.json(
          envelope({
            atc_class: "ALL",
            horizon_days: 14,
            model: "custom_test_model",
            uncertainty_method: "test_method",
            forecast: [{ date: "2019-10-09", prediction: 777.7, lower: 700.0, upper: 800.0 }],
            metrics: { mae: 12.34, rmse: 23.45, wape: 45.6, mase: 1.23 },
          }),
        ),
      ),
      http.get(`${API_BASE_URL}/api/v1/forecast/:atcClass/diagnostics`, () =>
        HttpResponse.json(
          envelope({
            atc_class: "ALL",
            model: "custom_test_model",
            metrics: { mae: 12.34, rmse: 23.45, wape: 45.6, mase: 1.23 },
            residual_diagnostics: {
              n_residuals: 999,
              mean_residual: 1.1,
              std_residual: 2.2,
              pct_days_underpredicted: 33.3,
              pct_days_overpredicted: 66.7,
              ljung_box: null,
              interpretation: "custom interpretation text",
            },
            performance_by_horizon_step: [],
            limitations: ["custom limitation text"],
          }),
        ),
      ),
    );
    renderForecast("/forecast");
    expect((await screen.findAllByText(/custom_test_model/)).length).toBeGreaterThan(0);
    expect(screen.getAllByText("45.6%").length).toBeGreaterThan(0); // WAPE from the custom fixture
    expect(screen.getByText("custom interpretation text")).toBeInTheDocument();
    expect(screen.getByText("custom limitation text")).toBeInTheDocument();
    expect(screen.queryByText(/ · ets ·/)).not.toBeInTheDocument();
    expect(screen.queryByText("16.3%")).not.toBeInTheDocument(); // the real aggregate WAPE
  });
});

describe("ForecastingPage — accessibility", () => {
  it("labels the ATC class control", async () => {
    renderForecast("/forecast");
    expect(await screen.findByLabelText("ATC class")).toBeInTheDocument();
  });

  it("renders the page heading and section headings", async () => {
    renderForecast("/forecast");
    expect(screen.getByRole("heading", { level: 1, name: "Forecasting Intelligence" })).toBeInTheDocument();
    expect(await screen.findByRole("heading", { name: "Diagnostics" })).toBeInTheDocument();
  });

  it("provides an accessible table alongside the chart, not chart-only access to the data", async () => {
    renderForecast("/forecast");
    expect(await screen.findByRole("table", { name: /Historical and forecast demand/ })).toBeInTheDocument();
  });
});
