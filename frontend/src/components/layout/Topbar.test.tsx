import { describe, expect, it, vi } from "vitest";
import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Route, Routes } from "react-router-dom";
import { renderWithProviders } from "../../test/testUtils";
import { Topbar } from "./Topbar";

function renderTopbar(route: string) {
  return renderWithProviders(
    <Routes>
      <Route path="/" element={<Topbar onMenuClick={vi.fn()} />} />
      <Route path="/demand" element={<Topbar onMenuClick={vi.fn()} />} />
      <Route path="/forecast/:atcClass" element={<Topbar onMenuClick={vi.fn()} />} />
    </Routes>,
    { route },
  );
}

describe("Topbar", () => {
  it("shows the Overview title at the root route", () => {
    renderTopbar("/");
    expect(screen.getByText("Overview")).toBeInTheDocument();
  });

  it("shows the matched section title for a nested route", () => {
    renderTopbar("/demand");
    expect(screen.getByText("Demand Intelligence")).toBeInTheDocument();
  });

  it("shows a breadcrumb suffix for a route with an :atcClass param", () => {
    renderTopbar("/forecast/N02BE");
    expect(screen.getByText("Forecasting")).toBeInTheDocument();
    expect(screen.getByText("N02BE")).toBeInTheDocument();
  });

  it("calls onMenuClick when the mobile nav trigger is clicked", async () => {
    // Mobile-only trigger (display:none at desktop widths in jsdom's
    // default viewport) — queried directly by attribute since the
    // accessible-name computation for a hidden element isn't reliable
    // through getByRole here; this test verifies the click handler is
    // wired, not the responsive visibility (covered by browser smoke test).
    const onMenuClick = vi.fn();
    const { container } = renderWithProviders(<Topbar onMenuClick={onMenuClick} />);
    const menuButton = container.querySelector<HTMLButtonElement>('button[aria-label="Open navigation"]');
    expect(menuButton).not.toBeNull();
    if (menuButton) await userEvent.click(menuButton);
    expect(onMenuClick).toHaveBeenCalledTimes(1);
  });

  it("does not render any fabricated user/account information", () => {
    renderTopbar("/");
    expect(screen.queryByText(/profile/i)).not.toBeInTheDocument();
    expect(screen.queryByRole("img", { name: /avatar/i })).not.toBeInTheDocument();
  });
});
