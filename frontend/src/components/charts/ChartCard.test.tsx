import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { ChartCard } from "./ChartCard";
import { EmptyState } from "../ui/EmptyState/EmptyState";
import { Skeleton } from "../ui/Skeleton/Skeleton";

describe("ChartCard", () => {
  it("renders a title and subtitle", () => {
    render(
      <ChartCard title="Weekly Sales Trend" subtitle="Rolling 12-week window">
        <div>chart placeholder</div>
      </ChartCard>,
    );
    expect(screen.getByRole("heading", { name: "Weekly Sales Trend" })).toBeInTheDocument();
    expect(screen.getByText("Rolling 12-week window")).toBeInTheDocument();
  });

  it("renders its children inside the chart area", () => {
    render(
      <ChartCard title="Weekly Sales Trend">
        <div data-testid="chart-content">chart placeholder</div>
      </ChartCard>,
    );
    expect(screen.getByTestId("chart-content")).toBeInTheDocument();
  });

  it("accepts a Skeleton as its child while loading, instead of fabricating chart data", () => {
    render(
      <ChartCard title="Weekly Sales Trend">
        <Skeleton variant="chart" />
      </ChartCard>,
    );
    expect(screen.getByRole("status", { name: "Loading" })).toBeInTheDocument();
  });

  it("accepts an EmptyState as its child when there is no data to chart", () => {
    render(
      <ChartCard title="Weekly Sales Trend">
        <EmptyState title="No data for this range" />
      </ChartCard>,
    );
    expect(screen.getByText("No data for this range")).toBeInTheDocument();
  });

  it("renders an optional header action", () => {
    render(
      <ChartCard title="Weekly Sales Trend" action={<button type="button">Export</button>}>
        <div>chart placeholder</div>
      </ChartCard>,
    );
    expect(screen.getByRole("button", { name: "Export" })).toBeInTheDocument();
  });

  it("renders an optional footer", () => {
    render(
      <ChartCard title="Weekly Sales Trend" footer={<div>legend</div>}>
        <div>chart placeholder</div>
      </ChartCard>,
    );
    expect(screen.getByText("legend")).toBeInTheDocument();
  });
});
