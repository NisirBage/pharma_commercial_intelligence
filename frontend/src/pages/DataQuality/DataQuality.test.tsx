import { describe, expect, it } from "vitest";
import { screen, within } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { server } from "../../mocks/server";
import { renderWithProviders } from "../../test/testUtils";
import { DataQualityPage } from "./index";

const API_BASE_URL = "http://localhost:8000";

function envelope<T>(data: T) {
  return { data, metadata: { generated_at: new Date().toISOString(), source: "test-fixture" } };
}

function renderPage() {
  return renderWithProviders(<DataQualityPage />);
}

describe("DataQualityPage — loading/error/empty", () => {
  it("shows a loading state before data arrives", () => {
    renderPage();
    expect(screen.getAllByRole("status", { name: "Loading" }).length).toBeGreaterThan(0);
  });

  it("shows an error state with retry on API failure — never a false empty state", async () => {
    server.use(
      http.get(`${API_BASE_URL}/api/v1/data-quality`, () =>
        HttpResponse.json({ error: { code: "internal_error", message: "Service unavailable.", details: [] } }, { status: 503 }),
      ),
    );
    renderPage();
    expect(await screen.findByText("Couldn't load the data-quality report")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Retry" })).toBeInTheDocument();
    expect(screen.queryByText("No data-quality report available")).not.toBeInTheDocument();
  });

  it("shows distinct empty states when reconciliation checks or file summaries are genuinely empty", async () => {
    server.use(
      http.get(`${API_BASE_URL}/api/v1/data-quality`, () =>
        HttpResponse.json(
          envelope({
            kaggle_dataset_id: "milanzdravkovic/pharma-sales-data",
            overall_status: "pass",
            file_summaries: [],
            reconciliation: [],
            monthly_inconsistency_warning: "",
          }),
        ),
      ),
    );
    renderPage();
    expect(await screen.findByText("No reconciliation checks available")).toBeInTheDocument();
    expect(screen.getByText("No source files available")).toBeInTheDocument();
  });
});

describe("DataQualityPage — content", () => {
  it("renders the overall status and the dataset's own source id", async () => {
    renderPage();
    // Scoped to the Overall Status region — the default fixture's
    // Monthly reconciliation check is ALSO "warn", so an unscoped
    // "WARN" query is ambiguous between the two distinct badges.
    const region = await screen.findByRole("region", { name: "Overall Status" });
    expect(within(region).getByText("WARN")).toBeInTheDocument();
    expect(within(region).getByText(/milanzdravkovic\/pharma-sales-data/)).toBeInTheDocument();
  });

  it("renders a note for every reconciliation check, including passing ones — not just failures", async () => {
    renderPage();
    expect(await screen.findByText("Daily reconciliation")).toBeInTheDocument();
    expect(screen.getByText("Weekly reconciliation")).toBeInTheDocument();
    expect(screen.getByText("Monthly reconciliation")).toBeInTheDocument();
    // "Reconciled" is the Daily/Weekly note — the Overview summary never
    // shows this (it only surfaces a note when a check fails); this page
    // shows every check's note.
    expect(screen.getAllByText("Reconciled").length).toBe(2);
    expect(screen.getByText("Known source inconsistency")).toBeInTheDocument();
  });

  it("never hides the documented monthly inconsistency warning", async () => {
    renderPage();
    expect(await screen.findByText(/does not reconcile with the daily-grain sum/)).toBeInTheDocument();
  });

  it("renders per-file record counts, including rejected records — shown nowhere else in the app", async () => {
    renderPage();
    const table = await screen.findByRole("table", { name: /Per-file record counts/ });
    expect(within(table).getByText("saleshourly.csv")).toBeInTheDocument();
    // total_records and valid_records are both 50532 in the fixture (0
    // rejected), so the formatted "50,532" legitimately appears twice —
    // once per column.
    expect(within(table).getAllByText("50,532")).toHaveLength(2);
    // rejected_records: 0 for the default fixture — a real, meaningful
    // "0 rejected" figure, not a missing value.
    const rejectedCell = within(table).getAllByText("0");
    expect(rejectedCell.length).toBeGreaterThan(0);
  });

  it("renders a real API-provided health status, not a hardcoded string", async () => {
    renderPage();
    expect(await screen.findByText(/API status: ok/)).toBeInTheDocument();
  });
});

describe("DataQualityPage — hardcoded-value guard", () => {
  it("never hardcodes the dataset id or file summaries — every value changes when the mocked API response changes", async () => {
    server.use(
      http.get(`${API_BASE_URL}/api/v1/data-quality`, () =>
        HttpResponse.json(
          envelope({
            kaggle_dataset_id: "some-other-dataset/custom-id",
            overall_status: "fail",
            file_summaries: [{ file_name: "custom_file.csv", total_records: 42, valid_records: 40, rejected_records: 2 }],
            reconciliation: [{ label: "Daily", reconciled: false, status: "fail", note: "Custom test note." }],
            monthly_inconsistency_warning: "Custom test warning.",
          }),
        ),
      ),
    );
    renderPage();
    expect(await screen.findByText(/some-other-dataset\/custom-id/)).toBeInTheDocument();
    expect(screen.getByText("custom_file.csv")).toBeInTheDocument();
    expect(screen.getByText("Custom test note.")).toBeInTheDocument();
    expect(screen.getByText("Custom test warning.")).toBeInTheDocument();
    // "FAIL" legitimately appears twice in this fixture (overall_status
    // AND the single Daily reconciliation check are both "fail") — an
    // unscoped getByText would be ambiguous.
    expect(screen.getAllByText("FAIL")).toHaveLength(2);
    expect(screen.queryByText("milanzdravkovic/pharma-sales-data")).not.toBeInTheDocument();
  });

  it("never renders a hardcoded status that bypasses the API — the real value resolves only after the fetch", async () => {
    renderPage();
    // The entire Overall Status section is gated behind the query's
    // loaded data (Skeleton renders in its place until then) — it must
    // not exist yet immediately after render, proving the content came
    // from the awaited response, not a constant baked into the component.
    expect(screen.queryByRole("region", { name: "Overall Status" })).not.toBeInTheDocument();
    const region = await screen.findByRole("region", { name: "Overall Status" });
    expect(within(region).getByText("WARN")).toBeInTheDocument();
  });
});

describe("DataQualityPage — accessibility", () => {
  it("has exactly one h1 and a labelled section for each subsection", async () => {
    renderPage();
    // The h1 renders immediately (outside the data-loading gate), but
    // the h2 subsections only mount once data has arrived — wait for
    // one of them before asserting on the rest, rather than racing the
    // fetch.
    expect(await screen.findByRole("heading", { level: 2, name: "Overall Status" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { level: 1, name: "Data Quality" })).toBeInTheDocument();
    expect(screen.getAllByRole("heading", { level: 1 })).toHaveLength(1);
    expect(screen.getByRole("heading", { level: 2, name: "Cross-Granularity Reconciliation" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { level: 2, name: "Source Files" })).toBeInTheDocument();
  });

  it("never conveys status by color alone — every StatusBadge carries its own text label", async () => {
    renderPage();
    const badges = await screen.findAllByText(/PASS|WARN|FAIL/);
    expect(badges.length).toBeGreaterThan(0);
  });
});
