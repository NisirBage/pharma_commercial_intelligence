import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { ChartTooltip } from "./ChartTooltip";

describe("ChartTooltip", () => {
  it("renders nothing when inactive", () => {
    const { container } = render(<ChartTooltip active={false} payload={[{ name: "Observed", value: 10 }]} />);
    expect(container).toBeEmptyDOMElement();
  });

  it("renders nothing when there is no payload", () => {
    const { container } = render(<ChartTooltip active payload={[]} />);
    expect(container).toBeEmptyDOMElement();
  });

  it("renders the label and each payload entry's name and value", () => {
    render(
      <ChartTooltip
        active
        label="2024-03-01"
        payload={[
          { name: "Observed", value: 128, color: "#2b3648" },
          { name: "Forecast", value: 131, color: "#1c4f9c" },
        ]}
      />,
    );
    expect(screen.getByText("2024-03-01")).toBeInTheDocument();
    expect(screen.getByText("Observed")).toBeInTheDocument();
    expect(screen.getByText("128")).toBeInTheDocument();
    expect(screen.getByText("Forecast")).toBeInTheDocument();
    expect(screen.getByText("131")).toBeInTheDocument();
  });

  it("applies a custom label formatter", () => {
    render(
      <ChartTooltip
        active
        label="2024-03-01"
        formatLabel={(l) => `Week of ${l}`}
        payload={[{ name: "Observed", value: 128 }]}
      />,
    );
    expect(screen.getByText("Week of 2024-03-01")).toBeInTheDocument();
  });
});
