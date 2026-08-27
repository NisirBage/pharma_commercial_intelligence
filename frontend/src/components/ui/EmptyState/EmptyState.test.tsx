import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { EmptyState } from "./EmptyState";

describe("EmptyState", () => {
  it("renders a title", () => {
    render(<EmptyState title="No records found" />);
    expect(screen.getByText("No records found")).toBeInTheDocument();
  });

  it("renders an optional description", () => {
    render(<EmptyState title="No records found" description="Try widening the date range." />);
    expect(screen.getByText("Try widening the date range.")).toBeInTheDocument();
  });

  it("omits the description when none is given", () => {
    render(<EmptyState title="No records found" />);
    expect(screen.queryByText("Try widening the date range.")).not.toBeInTheDocument();
  });

  it("renders an optional action", () => {
    render(<EmptyState title="No records found" action={<button type="button">Reset filters</button>} />);
    expect(screen.getByRole("button", { name: "Reset filters" })).toBeInTheDocument();
  });
});
