import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { SectionHeader } from "./SectionHeader";

describe("SectionHeader", () => {
  it("renders the title as a heading", () => {
    render(<SectionHeader title="Demand Intelligence" />);
    expect(screen.getByRole("heading", { name: "Demand Intelligence" })).toBeInTheDocument();
  });

  it("renders at the requested heading level", () => {
    render(<SectionHeader title="Overview" as="h1" />);
    expect(screen.getByRole("heading", { level: 1, name: "Overview" })).toBeInTheDocument();
  });

  it("defaults to an h2", () => {
    render(<SectionHeader title="Trends" />);
    expect(screen.getByRole("heading", { level: 2, name: "Trends" })).toBeInTheDocument();
  });

  it("renders an optional eyebrow and description", () => {
    render(<SectionHeader eyebrow="Section" title="Trends" description="Weekly sales trend detail." />);
    expect(screen.getByText("Section")).toBeInTheDocument();
    expect(screen.getByText("Weekly sales trend detail.")).toBeInTheDocument();
  });

  it("renders an optional trailing action", () => {
    render(<SectionHeader title="Trends" action={<button type="button">Export</button>} />);
    expect(screen.getByRole("button", { name: "Export" })).toBeInTheDocument();
  });

  it("applies an id to the heading element so a landmark can reference it via aria-labelledby", () => {
    render(<SectionHeader title="Trends" id="trends-heading" />);
    expect(screen.getByRole("heading", { name: "Trends" })).toHaveAttribute("id", "trends-heading");
  });
});
