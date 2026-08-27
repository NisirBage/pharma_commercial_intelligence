import type { ReactElement, ReactNode } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, type RenderOptions } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";

/** A fresh QueryClient per render — no cache leakage between tests, and
 * retries disabled so an intentionally-erroring test doesn't hang on
 * TanStack Query's default retry/backoff. */
export function createTestQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false, gcTime: 0 },
      mutations: { retry: false },
    },
  });
}

interface RenderWithProvidersOptions extends Omit<RenderOptions, "wrapper"> {
  route?: string;
  queryClient?: QueryClient;
}

/** Wraps a component with the same providers main.tsx installs
 * (QueryClientProvider, a router) so component tests exercise real
 * hook/routing behavior instead of a bare component in isolation. */
export function renderWithProviders(ui: ReactElement, options: RenderWithProvidersOptions = {}) {
  const { route = "/", queryClient = createTestQueryClient(), ...renderOptions } = options;

  function Wrapper({ children }: { children: ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={[route]}>{children}</MemoryRouter>
      </QueryClientProvider>
    );
  }

  return { queryClient, ...render(ui, { wrapper: Wrapper, ...renderOptions }) };
}
