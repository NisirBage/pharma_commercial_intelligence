import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Tabs, type TabItem } from "./Tabs";

const items: TabItem[] = [
  { value: "trends", label: "Trends" },
  { value: "atc", label: "ATC Analysis" },
  { value: "seasonality", label: "Seasonality" },
];

describe("Tabs", () => {
  it("marks the current value's tab as selected", () => {
    render(<Tabs items={items} value="atc" onChange={() => {}} ariaLabel="Demand Intelligence sections" />);
    expect(screen.getByRole("tab", { name: "ATC Analysis" })).toHaveAttribute("aria-selected", "true");
    expect(screen.getByRole("tab", { name: "Trends" })).toHaveAttribute("aria-selected", "false");
  });

  it("calls onChange when a tab is clicked", async () => {
    const onChange = vi.fn();
    render(<Tabs items={items} value="trends" onChange={onChange} ariaLabel="Demand Intelligence sections" />);
    await userEvent.click(screen.getByRole("tab", { name: "Seasonality" }));
    expect(onChange).toHaveBeenCalledWith("seasonality");
  });

  it("supports arrow-key navigation between tabs", async () => {
    const onChange = vi.fn();
    render(<Tabs items={items} value="trends" onChange={onChange} ariaLabel="Demand Intelligence sections" />);
    screen.getByRole("tab", { name: "Trends" }).focus();
    await userEvent.keyboard("{ArrowRight}");
    expect(onChange).toHaveBeenCalledWith("atc");
  });

  it("wraps around with ArrowLeft from the first tab", async () => {
    const onChange = vi.fn();
    render(<Tabs items={items} value="trends" onChange={onChange} ariaLabel="Demand Intelligence sections" />);
    screen.getByRole("tab", { name: "Trends" }).focus();
    await userEvent.keyboard("{ArrowLeft}");
    expect(onChange).toHaveBeenCalledWith("seasonality");
  });

  it("does not hardcode any business-domain labels — the caller supplies them", () => {
    const customItems: TabItem[] = [{ value: "x", label: "Custom Section" }];
    render(<Tabs items={customItems} value="x" onChange={() => {}} ariaLabel="Custom" />);
    expect(screen.getByRole("tab", { name: "Custom Section" })).toBeInTheDocument();
  });
});
