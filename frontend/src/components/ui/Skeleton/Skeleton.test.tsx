import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { Skeleton } from "./Skeleton";

describe("Skeleton", () => {
  it("announces a loading status for screen reader users", () => {
    render(<Skeleton variant="text" />);
    expect(screen.getByRole("status", { name: "Loading" })).toBeInTheDocument();
  });

  it("renders the requested number of text lines", () => {
    const { container } = render(<Skeleton variant="text" count={4} />);
    expect(container.querySelectorAll("[class*='textLine']")).toHaveLength(4);
  });

  it("renders a metric variant", () => {
    render(<Skeleton variant="metric" />);
    expect(screen.getByRole("status")).toBeInTheDocument();
  });

  it("renders a table variant with the requested row count", () => {
    const { container } = render(<Skeleton variant="table" count={5} />);
    expect(container.querySelectorAll("[class*='tableRow']")).toHaveLength(5);
  });

  it("renders a chart variant", () => {
    render(<Skeleton variant="chart" />);
    expect(screen.getByRole("status")).toBeInTheDocument();
  });
});
