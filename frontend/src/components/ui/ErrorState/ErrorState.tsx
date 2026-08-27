import { AlertTriangle } from "lucide-react";
import { describeApiError } from "../../../api/client";
import { Button } from "../Button/Button";
import styles from "./ErrorState.module.css";

export interface ErrorStateProps {
  title?: string;
  /** The raw error, typically from a TanStack Query `error` field. Passed
   * through `describeApiError` — never rendered as a raw message/stack
   * trace. Ignored if `message` is supplied directly. */
  error?: unknown;
  message?: string;
  onRetry?: () => void;
}

/** Shown when a query fails. Always resolves to a safe, human-readable
 * message via the existing api/client.ts error architecture — never
 * surfaces a backend stack trace or raw Error.message. */
export function ErrorState({ title = "Something went wrong", error, message, onRetry }: ErrorStateProps) {
  const description = message ?? (error !== undefined ? describeApiError(error) : "Please try again.");

  return (
    <div className={styles.wrapper} role="alert">
      <div className={styles.icon} aria-hidden="true">
        <AlertTriangle size={28} strokeWidth={1.5} />
      </div>
      <p className={styles.title}>{title}</p>
      <p className={styles.description}>{description}</p>
      {onRetry && (
        <div className={styles.action}>
          <Button variant="secondary" size="sm" onClick={onRetry}>
            Retry
          </Button>
        </div>
      )}
    </div>
  );
}
