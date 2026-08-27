import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Button } from "./Button";

describe("Button", () => {
  it("renders children and responds to a click", async () => {
    const onClick = vi.fn();
    render(<Button onClick={onClick}>Run optimization</Button>);
    await userEvent.click(screen.getByRole("button", { name: "Run optimization" }));
    expect(onClick).toHaveBeenCalledOnce();
  });

  it.each(["primary", "secondary", "ghost", "danger"] as const)("renders the %s variant", (variant) => {
    render(<Button variant={variant}>Action</Button>);
    expect(screen.getByRole("button", { name: "Action" })).toBeInTheDocument();
  });

  it("is disabled and does not fire onClick when disabled", async () => {
    const onClick = vi.fn();
    render(
      <Button disabled onClick={onClick}>
        Run
      </Button>,
    );
    const button = screen.getByRole("button", { name: "Run" });
    expect(button).toBeDisabled();
    await userEvent.click(button);
    expect(onClick).not.toHaveBeenCalled();
  });

  it("shows a loading state, disables itself, and prevents duplicate submission", async () => {
    const onClick = vi.fn();
    render(
      <Button loading onClick={onClick}>
        Run
      </Button>,
    );
    const button = screen.getByRole("button", { name: "Run" });
    expect(button).toBeDisabled();
    expect(button).toHaveAttribute("aria-busy", "true");
    await userEvent.click(button);
    expect(onClick).not.toHaveBeenCalled();
  });

  it("supports an accessible label for icon-only usage", () => {
    render(<Button icon={<span data-testid="icon" />} aria-label="Refresh" />);
    expect(screen.getByRole("button", { name: "Refresh" })).toBeInTheDocument();
  });

  it("is keyboard activatable (native button semantics)", async () => {
    const onClick = vi.fn();
    render(<Button onClick={onClick}>Run</Button>);
    const button = screen.getByRole("button", { name: "Run" });
    button.focus();
    await userEvent.keyboard("{Enter}");
    expect(onClick).toHaveBeenCalledOnce();
  });
});
