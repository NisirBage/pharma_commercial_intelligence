import { describe, expect, it } from "vitest";
import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Route, Routes } from "react-router-dom";
import { renderWithProviders } from "../../test/testUtils";
import { AppShell } from "./AppShell";

function renderShell(route = "/") {
  return renderWithProviders(
    <Routes>
      <Route path="/" element={<AppShell />}>
        <Route index element={<div>Overview content</div>} />
        <Route path="demand" element={<div>Demand content</div>} />
      </Route>
    </Routes>,
    { route },
  );
}

describe("AppShell", () => {
  it("renders the matched child route inside the main content area", () => {
    renderShell("/");
    expect(screen.getByRole("main")).toHaveTextContent("Overview content");
  });

  it("renders the sidebar navigation and topbar together", () => {
    renderShell("/");
    expect(screen.getByRole("navigation", { name: "Primary" })).toBeInTheDocument();
    expect(screen.getByRole("banner")).toBeInTheDocument();
  });

  it("shows a page title in the topbar that matches the active section", () => {
    renderShell("/demand");
    expect(screen.getByRole("banner")).toHaveTextContent("Demand Intelligence");
    expect(screen.getByText("Demand content")).toBeInTheDocument();
  });

  it("opens the mobile navigation drawer from the topbar menu button", async () => {
    // The menu/close triggers are mobile-only (display:none at desktop
    // widths via CSS, which is genuinely applied in jsdom here), so
    // they're queried directly by attribute — this test exercises the
    // wiring, not the responsive visibility, which the browser smoke
    // test covers separately.
    const { container } = renderShell("/");
    const nav = screen.getByRole("navigation", { name: "Primary" });
    expect(nav.className).not.toMatch(/open/);
    const menuButton = container.querySelector<HTMLButtonElement>('button[aria-label="Open navigation"]');
    expect(menuButton).not.toBeNull();
    if (menuButton) await userEvent.click(menuButton);
    expect(nav.className).toMatch(/open/);
  });

  it("closes the mobile navigation drawer from the sidebar's close button", async () => {
    const { container } = renderShell("/");
    const menuButton = container.querySelector<HTMLButtonElement>('button[aria-label="Open navigation"]');
    if (menuButton) await userEvent.click(menuButton);
    const nav = screen.getByRole("navigation", { name: "Primary" });
    expect(nav.className).toMatch(/open/);
    const closeButton = container.querySelector<HTMLButtonElement>('button[aria-label="Close navigation"]');
    expect(closeButton).not.toBeNull();
    if (closeButton) await userEvent.click(closeButton);
    expect(nav.className).not.toMatch(/open/);
  });

  it("renders a skip link targeting the main content region", () => {
    renderShell("/");
    expect(screen.getByRole("link", { name: "Skip to main content" })).toHaveAttribute("href", "#main-content");
    expect(screen.getByRole("main")).toHaveAttribute("id", "main-content");
  });
});
