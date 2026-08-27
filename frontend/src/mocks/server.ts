import { setupServer } from "msw/node";
import { handlers } from "./handlers";

/** Node-side MSW server for Vitest — every component/hook/API-client test
 * runs against this instead of a real backend (M7 Sec. "mocking"). */
export const server = setupServer(...handlers);
