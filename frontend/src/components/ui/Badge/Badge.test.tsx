import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { Badge } from "./Badge";

describe("Badge", () => {
  it.each(["neutral", "info", "success", "warning", "danger"] as const)("renders the %s variant with its text", (variant) => {
    render(<Badge variant={variant}>Label</Badge>);
    expect(screen.getByText("Label")).toBeInTheDocument();
  });

  it("defaults to neutral when no variant is given", () => {
    render(<Badge>Default</Badge>);
    expect(screen.getByText("Default")).toBeInTheDocument();
  });
});
