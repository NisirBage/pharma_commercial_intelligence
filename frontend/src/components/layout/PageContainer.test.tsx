import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { PageContainer } from "./PageContainer";

describe("PageContainer", () => {
  it("renders its children", () => {
    render(
      <PageContainer>
        <p>Page body</p>
      </PageContainer>,
    );
    expect(screen.getByText("Page body")).toBeInTheDocument();
  });
});
