/**
 * Centralized cache tuning — matches M6's own caching architecture
 * (backend/app/services/cache.py): the two expensive backend computations
 * (the canonical demand frame; per-class demand inputs, which rerun an M4
 * backtest to recover residuals) are process-lifetime cached server-side,
 * so the frontend should not aggressively refetch them either. See
 * docs/frontend-architecture.md, "Caching strategy".
 */
export const STALE_TIME = {
  /** Rarely changes within a session — the underlying dataset is static
   * (a fixed historical Kaggle export, not a live feed). */
  LONG: 15 * 60 * 1000,
  /** Moderate — filtered views (trends, anomalies) a user might revisit
   * with different parameters. */
  MEDIUM: 5 * 60 * 1000,
  /** Expensive on the backend the first time (M4 cache warm-up, ~9s) —
   * cache aggressively so navigating between pages doesn't re-trigger it. */
  FORECAST: 30 * 60 * 1000,
} as const;
