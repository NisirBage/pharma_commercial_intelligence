import { useNavigate, useParams } from "react-router-dom";
import { SectionHeader } from "../../components/ui/SectionHeader/SectionHeader";
import { Select } from "../../components/ui/Select/Select";
import { useForecast } from "../../hooks/useForecast";
import { useForecastDiagnostics } from "../../hooks/useForecastDiagnostics";
import { useSalesTrends } from "../../hooks/useSalesTrends";
import { ATC_SELECT_OPTIONS } from "../../lib/atcOptions";
import { isKnownAtcClass } from "../../types/api";
import { NotFoundPage } from "../NotFound";
import { ForecastChart } from "./ForecastChart";
import { ForecastDiagnosticsSection } from "./ForecastDiagnostics";
import styles from "./Forecasting.module.css";
import { ForecastOverview } from "./ForecastOverview";

const HISTORY_WINDOW_DAYS = 60;

/**
 * Forecasting Intelligence — M7.6. Unlike Demand Intelligence's
 * `?tab=`, this page's ATC selection is a route param (`:atcClass`),
 * already established by router.tsx before this milestone (the
 * comment there: "optional :atcClass") — the Select below navigates
 * rather than holding local filter state, so the URL is always the
 * single source of truth (refresh/back/forward all just work, for
 * free, via the router). There is no grain/horizon/date-range
 * control: the three forecast endpoints take no query parameters at
 * all (verified against backend/app/api/routes/forecasts.py) — the
 * only thing this page lets a user choose is which series to forecast.
 *
 * A single coherent surface, not tabs: `useForecast` and
 * `useForecastDiagnostics` are two independent, lightweight
 * queries (14 forecast points; a handful of diagnostic fields) that
 * both directly serve "how trustworthy is this forecast" — the
 * decision workflow is clearer with both visible together than
 * behind a second click.
 */
export function ForecastingPage() {
  const { atcClass } = useParams<{ atcClass?: string }>();
  const navigate = useNavigate();
  const isValid = !atcClass || isKnownAtcClass(atcClass);
  // An unrecognized :atcClass renders NotFoundPage below, but every
  // hook must still be called on every render (rules-of-hooks) — so an
  // invalid class is treated as "no class" for the queries themselves
  // rather than firing a request the backend would just 404 anyway.
  const validAtcClass = isValid ? atcClass : undefined;

  // GET /api/v1/forecast/aggregate is a dedicated path (param
  // omitted); GET /api/v1/forecast/{atc_class}/diagnostics instead
  // takes the literal string "ALL" for the aggregate (verified in
  // forecast_service.py — KNOWN_FORECAST_ENTITIES includes "ALL", and
  // useForecastDiagnostics's required `string` param already reflects
  // this). Two different conventions for "aggregate" on two endpoints
  // of the same feature — each honored exactly, not unified by guessing.
  const forecastQuery = useForecast(validAtcClass);
  const diagnosticsQuery = useForecastDiagnostics(validAtcClass ?? "ALL");
  // GET /api/v1/sales/trends has no "recent window" parameter, so the
  // full series is fetched (same as Demand Intelligence's Trends tab
  // default) and sliced to the trailing HISTORY_WINDOW_DAYS client-side
  // — consistent with that page's already-verified-performant pattern,
  // rather than adding a dependent-query stage or changing this shared
  // hook's signature for one page.
  const historyQuery = useSalesTrends({ atcClass: validAtcClass, grain: "daily" });

  function handleAtcChange(value: string) {
    navigate(value ? `/forecast/${value}` : "/forecast");
  }

  if (!isValid) {
    return <NotFoundPage message={`"${atcClass}" is not a recognized ATC class.`} />;
  }

  return (
    <div className={styles.page}>
      <SectionHeader
        as="h1"
        title="Forecasting Intelligence"
        description="Expected demand over the next horizon, how it compares with recent history, and how much to trust it."
      />

      <div className={styles.controls}>
        <div className={styles.controlField}>
          <Select
            label="ATC class"
            options={ATC_SELECT_OPTIONS}
            value={atcClass ?? ""}
            onChange={(e) => handleAtcChange(e.target.value)}
          />
        </div>
      </div>

      <ForecastOverview forecastQuery={forecastQuery} historyQuery={historyQuery} />

      <ForecastChart forecastQuery={forecastQuery} historyQuery={historyQuery} historyWindowDays={HISTORY_WINDOW_DAYS} />

      <ForecastDiagnosticsSection query={diagnosticsQuery} />
    </div>
  );
}
