import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Select } from "./Select";

const options = [
  { value: "N02BE", label: "N02BE" },
  { value: "R03", label: "R03" },
];

describe("Select", () => {
  it("renders a labeled native select with the given options", () => {
    render(<Select label="ATC class" options={options} value="N02BE" onChange={() => {}} />);
    const select = screen.getByLabelText("ATC class");
    expect(select).toBeInTheDocument();
    expect(screen.getByRole("option", { name: "R03" })).toBeInTheDocument();
  });

  it("calls onChange with the newly selected value", async () => {
    const onChange = vi.fn();
    render(<Select label="ATC class" options={options} value="N02BE" onChange={onChange} />);
    await userEvent.selectOptions(screen.getByLabelText("ATC class"), "R03");
    expect(onChange).toHaveBeenCalled();
  });

  it("renders helper text when provided", () => {
    render(<Select label="Grain" options={options} helperText="Rollup grain for the trend chart." onChange={() => {}} />);
    expect(screen.getByText("Rollup grain for the trend chart.")).toBeInTheDocument();
  });

  it("renders an accessible error message and marks the field invalid", () => {
    render(<Select label="ATC class" options={options} error="Unknown ATC class." onChange={() => {}} />);
    expect(screen.getByRole("alert")).toHaveTextContent("Unknown ATC class.");
    expect(screen.getByLabelText("ATC class")).toHaveAttribute("aria-invalid", "true");
  });

  it("respects the disabled prop", () => {
    render(<Select label="ATC class" options={options} disabled onChange={() => {}} />);
    expect(screen.getByLabelText("ATC class")).toBeDisabled();
  });
});
