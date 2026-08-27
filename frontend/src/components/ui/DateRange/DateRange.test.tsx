import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { DateRange } from "./DateRange";

describe("DateRange", () => {
  it("renders accessible labeled start and end date inputs", () => {
    render(
      <DateRange startValue="2020-01-01" endValue="2020-06-01" onStartChange={() => {}} onEndChange={() => {}} />,
    );
    expect(screen.getByLabelText("Start date")).toHaveValue("2020-01-01");
    expect(screen.getByLabelText("End date")).toHaveValue("2020-06-01");
  });

  it("calls onStartChange when the start date changes", async () => {
    const onStartChange = vi.fn();
    render(
      <DateRange
        startValue="2020-01-01"
        endValue="2020-06-01"
        onStartChange={onStartChange}
        onEndChange={() => {}}
      />,
    );
    const startInput = screen.getByLabelText("Start date");
    await userEvent.clear(startInput);
    await userEvent.type(startInput, "2020-02-01");
    expect(onStartChange).toHaveBeenCalled();
  });

  it("constrains the end input's min to the start value", () => {
    render(
      <DateRange startValue="2020-01-01" endValue="2020-06-01" onStartChange={() => {}} onEndChange={() => {}} />,
    );
    expect(screen.getByLabelText("End date")).toHaveAttribute("min", "2020-01-01");
  });

  it("disables both inputs when disabled is set", () => {
    render(
      <DateRange
        startValue="2020-01-01"
        endValue="2020-06-01"
        onStartChange={() => {}}
        onEndChange={() => {}}
        disabled
      />,
    );
    expect(screen.getByLabelText("Start date")).toBeDisabled();
    expect(screen.getByLabelText("End date")).toBeDisabled();
  });

  it("renders an accessible error message when provided", () => {
    render(
      <DateRange
        startValue="2020-06-01"
        endValue="2020-01-01"
        onStartChange={() => {}}
        onEndChange={() => {}}
        error="Start date must be before end date."
      />,
    );
    expect(screen.getByRole("alert")).toHaveTextContent("Start date must be before end date.");
  });
});
