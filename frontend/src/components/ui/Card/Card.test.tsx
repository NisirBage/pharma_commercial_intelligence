import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { Card } from "./Card";

describe("Card", () => {
  it("renders title, subtitle, and content", () => {
    render(
      <Card title="ATC Performance" subtitle="8 observed classes">
        <p>Body content</p>
      </Card>,
    );
    expect(screen.getByRole("heading", { name: "ATC Performance" })).toBeInTheDocument();
    expect(screen.getByText("8 observed classes")).toBeInTheDocument();
    expect(screen.getByText("Body content")).toBeInTheDocument();
  });

  it("renders a header action and footer when provided", () => {
    render(
      <Card title="Forecast" headerAction={<button type="button">Export</button>} footer={<span>Updated just now</span>}>
        content
      </Card>,
    );
    expect(screen.getByRole("button", { name: "Export" })).toBeInTheDocument();
    expect(screen.getByText("Updated just now")).toBeInTheDocument();
  });

  it("renders without a header when no title/subtitle/action is given", () => {
    render(<Card>Just content</Card>);
    expect(screen.queryByRole("heading")).not.toBeInTheDocument();
    expect(screen.getByText("Just content")).toBeInTheDocument();
  });
});
