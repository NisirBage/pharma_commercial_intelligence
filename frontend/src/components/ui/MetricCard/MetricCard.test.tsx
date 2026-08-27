import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MetricCard } from "./MetricCard";

describe("MetricCard", () => {
  it("renders the label and value passed in by the caller", () => {
    render(<MetricCard label="Forecast MAPE" value="12.4%" />);
    expect(screen.getByText("Forecast MAPE")).toBeInTheDocument();
    expect(screen.getByText("12.4%")).toBeInTheDocument();
  });

  it("renders an optional unit", () => {
    render(<MetricCard label="Units on hand" value="8,420" unit="units" />);
    expect(screen.getByText("units")).toBeInTheDocument();
  });

  it("renders trend text when both trend and trendDirection are supplied", () => {
    render(<MetricCard label="Coverage" value="94%" trend="+2.1 pts vs. prior period" trendDirection="up" />);
    expect(screen.getByText("+2.1 pts vs. prior period")).toBeInTheDocument();
  });

  it("renders an optional status badge", () => {
    render(<MetricCard label="Data freshness" value="Current" status="healthy" />);
    expect(screen.getByText("Healthy")).toBeInTheDocument();
  });

  it("renders helper text when provided", () => {
    render(<MetricCard label="Backtest window" value="12 folds" helperText="Rolling-origin cross-validation." />);
    expect(screen.getByText("Rolling-origin cross-validation.")).toBeInTheDocument();
  });

  it("exposes a tooltip explaining the metric via an accessible trigger", async () => {
    render(<MetricCard label="MAPE" value="12.4%" tooltip="Mean Absolute Percentage Error." />);
    const trigger = screen.getByRole("button", { name: "About MAPE" });
    await userEvent.tab();
    expect(trigger).toHaveFocus();
    expect(screen.getByRole("tooltip")).toHaveTextContent("Mean Absolute Percentage Error.");
  });

  it("does not hardcode any example business values into the rendered output", () => {
    render(<MetricCard label="Custom metric" value="N/A" />);
    expect(screen.queryByText(/2\.4M/)).not.toBeInTheDocument();
    expect(screen.queryByText(/\+4\.8%/)).not.toBeInTheDocument();
  });
});
