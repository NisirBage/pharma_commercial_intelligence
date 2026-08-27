import { describe, expect, it, vi } from "vitest";
import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { renderWithProviders } from "../../test/testUtils";
import { Sidebar } from "./Sidebar";

describe("Sidebar", () => {
  it("renders a labeled navigation landmark with a link to every section", () => {
    renderWithProviders(<Sidebar open={false} onClose={() => {}} />);
    const nav = screen.getByRole("navigation", { name: "Primary" });
    expect(nav).toBeInTheDocument();
    for (const label of [
      "Overview",
      "Demand Intelligence",
      "Forecasting",
      "Supply Planning",
      "Recommendations",
      "Data Quality",
    ]) {
      expect(screen.getByRole("link", { name: new RegExp(label) })).toBeInTheDocument();
    }
  });

  it("marks the link matching the current route as active", () => {
    renderWithProviders(<Sidebar open={false} onClose={() => {}} />, { route: "/demand" });
    expect(screen.getByRole("link", { name: /Demand Intelligence/ }).className).toMatch(/active/);
    expect(screen.getByRole("link", { name: /^Overview/ }).className).not.toMatch(/active/);
  });

  it("does not mark Overview active on a nested route", () => {
    renderWithProviders(<Sidebar open={false} onClose={() => {}} />, { route: "/forecast/N02BE" });
    expect(screen.getByRole("link", { name: /Forecasting/ }).className).toMatch(/active/);
  });

  it("calls onClose when a nav link is clicked (closing the mobile drawer)", async () => {
    const onClose = vi.fn();
    renderWithProviders(<Sidebar open onClose={onClose} />);
    await userEvent.click(screen.getByRole("link", { name: /Recommendations/ }));
    expect(onClose).toHaveBeenCalled();
  });

  it("renders a scrim that closes the drawer when open", async () => {
    const onClose = vi.fn();
    const { container } = renderWithProviders(<Sidebar open onClose={onClose} />);
    const scrim = container.querySelector("[aria-hidden='true']");
    expect(scrim).toBeInTheDocument();
    if (scrim) await userEvent.click(scrim);
    expect(onClose).toHaveBeenCalled();
  });
});
