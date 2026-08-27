import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { ChartLegend } from "./ChartLegend";

describe("ChartLegend", () => {
  it("renders a label for each item", () => {
    render(
      <ChartLegend
        items={[
          { label: "Observed", color: "#2b3648" },
          { label: "Forecast", color: "#1c4f9c" },
        ]}
      />,
    );
    expect(screen.getByText("Observed")).toBeInTheDocument();
    expect(screen.getByText("Forecast")).toBeInTheDocument();
  });

  it("renders nothing when given an empty item list", () => {
    const { container } = render(<ChartLegend items={[]} />);
    expect(container).toBeEmptyDOMElement();
  });

  it("never relies on color alone — every swatch has an adjacent text label", () => {
    render(<ChartLegend items={[{ label: "Confidence interval", color: "#c3d5ee", variant: "area" }]} />);
    const swatch = document.querySelector('[aria-hidden="true"]');
    expect(swatch).toBeInTheDocument();
    expect(screen.getByText("Confidence interval")).toBeInTheDocument();
  });
});
