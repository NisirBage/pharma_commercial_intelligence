import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ErrorState } from "./ErrorState";
import { ApiError, ApiNetworkError } from "../../../api/client";

describe("ErrorState", () => {
  it("renders as an alert with a title and message", () => {
    render(<ErrorState message="Could not load forecast data." />);
    expect(screen.getByRole("alert")).toHaveTextContent("Could not load forecast data.");
  });

  it("translates an ApiError via the shared error-description helper, never a raw stack trace", () => {
    const error = new ApiError(503, "service_unavailable", "This service is temporarily unavailable. Please try again shortly.");
    render(<ErrorState error={error} />);
    expect(screen.getByRole("alert")).toHaveTextContent("This service is temporarily unavailable. Please try again shortly.");
  });

  it("translates an ApiNetworkError into its safe message", () => {
    render(<ErrorState error={new ApiNetworkError()} />);
    expect(screen.getByRole("alert")).toHaveTextContent("Unable to reach the API");
  });

  it("renders a retry action and calls onRetry when clicked", async () => {
    const onRetry = vi.fn();
    render(<ErrorState message="Failed." onRetry={onRetry} />);
    await userEvent.click(screen.getByRole("button", { name: "Retry" }));
    expect(onRetry).toHaveBeenCalledTimes(1);
  });

  it("omits the retry action when onRetry is not supplied", () => {
    render(<ErrorState message="Failed." />);
    expect(screen.queryByRole("button", { name: "Retry" })).not.toBeInTheDocument();
  });
});
