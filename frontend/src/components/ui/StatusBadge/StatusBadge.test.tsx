import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { StatusBadge } from "./StatusBadge";

describe("StatusBadge", () => {
  it.each([
    ["healthy", "Healthy"],
    ["warning", "Warning"],
    ["error", "Error"],
    ["available", "Available"],
    ["unavailable", "Unavailable"],
    ["pending", "Pending"],
  ] as const)("renders the default label for status=%s", (status, expectedLabel) => {
    render(<StatusBadge status={status} />);
    expect(screen.getByText(expectedLabel)).toBeInTheDocument();
  });

  it("allows overriding the label text while keeping the status semantics", () => {
    render(<StatusBadge status="error" label="Forecasting service unavailable" />);
    expect(screen.getByText("Forecasting service unavailable")).toBeInTheDocument();
  });

  it("never conveys status by color alone — an icon is always present", () => {
    const { container } = render(<StatusBadge status="warning" />);
    expect(container.querySelector("svg")).toBeInTheDocument();
  });
});
