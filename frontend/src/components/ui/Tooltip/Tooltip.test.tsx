import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Tooltip } from "./Tooltip";

describe("Tooltip", () => {
  it("renders the tooltip content in the document, associated via aria-describedby", () => {
    render(
      <Tooltip content="Mean Absolute Percentage Error across the backtest window.">
        <button type="button">MAPE</button>
      </Tooltip>,
    );
    expect(screen.getByRole("tooltip")).toHaveTextContent(
      "Mean Absolute Percentage Error across the backtest window.",
    );
  });

  it("shows the tooltip on focus, so keyboard users can access it", async () => {
    render(
      <Tooltip content="Service level definition.">
        <button type="button">Service level</button>
      </Tooltip>,
    );
    const tooltip = screen.getByRole("tooltip");
    expect(tooltip.className).not.toMatch(/visible/);
    await userEvent.tab();
    expect(screen.getByRole("button", { name: "Service level" })).toHaveFocus();
    expect(tooltip.className).toMatch(/visible/);
  });

  it("hides the tooltip on blur", async () => {
    render(
      <>
        <Tooltip content="Definition.">
          <button type="button">Term</button>
        </Tooltip>
        <button type="button">Elsewhere</button>
      </>,
    );
    await userEvent.tab();
    const tooltip = screen.getByRole("tooltip");
    expect(tooltip.className).toMatch(/visible/);
    await userEvent.tab();
    expect(tooltip.className).not.toMatch(/visible/);
  });
});
