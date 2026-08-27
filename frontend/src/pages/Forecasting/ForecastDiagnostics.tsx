import type { UseQueryResult } from "@tanstack/react-query";
import { Badge } from "../../components/ui/Badge/Badge";
import { Card } from "../../components/ui/Card/Card";
import { EmptyState } from "../../components/ui/EmptyState/EmptyState";
import { ErrorState } from "../../components/ui/ErrorState/ErrorState";
import { MetricCard } from "../../components/ui/MetricCard/MetricCard";
import { SectionHeader } from "../../components/ui/SectionHeader/SectionHeader";
import { Table, type TableColumn } from "../../components/ui/Table/Table";
import { getAutocorrelationDisplay } from "../../lib/domainLabels";
import { formatCV, formatDecimal, formatPValue, formatPercent } from "../../lib/format";
import type { ForecastDiagnosticsResponse, HorizonStepError } from "../../types/api";
import styles from "./Forecasting.module.css";

export interface ForecastDiagnosticsSectionProps {
  query: UseQueryResult<ForecastDiagnosticsResponse, unknown>;
}

const horizonColumns: TableColumn<HorizonStepError>[] = [
  { key: "step", header: "Horizon Step", render: (row) => `Day ${row.horizon_step}` },
  { key: "mae", header: "MAE", align: "end", render: (row) => formatDecimal(row.mae) },
  { key: "n", header: "Observations", align: "end", render: (row) => String(row.n_observations) },
];

/** How trustworthy is this forecast? GET
 * /api/v1/forecast/{atc_class}/diagnostics — M4's backtest-derived
 * accuracy metrics, residual diagnostics, and explicit limitations,
 * all read directly. No "model health score" is invented: every
 * number here is either an API field or (for nothing in this
 * component) a transparently-labeled derivation. */
export function ForecastDiagnosticsSection({ query }: ForecastDiagnosticsSectionProps) {
  const { data, isLoading, isError, error, refetch } = query;

  return (
    <section aria-labelledby="diagnostics-heading" className={styles.sectionStack}>
      <SectionHeader
        id="diagnostics-heading"
        eyebrow="Trust"
        title="Diagnostics"
        description="Backtest accuracy and residual behavior for the selected forecast model."
      />

      {isError ? (
        <ErrorState title="Couldn't load forecast diagnostics" error={error} onRetry={() => refetch()} />
      ) : isLoading ? (
        <div className={styles.diagnosticsGrid}>
          <MetricCard label="MAE" loading />
          <MetricCard label="RMSE" loading />
          <MetricCard label="WAPE" loading />
          <MetricCard label="MASE" loading />
        </div>
      ) : !data ? (
        <EmptyState title="No diagnostics available" />
      ) : (
        <>
          <div className={styles.diagnosticsGrid}>
            <MetricCard label="MAE" value={formatDecimal(data.metrics.mae)} tooltip="Mean Absolute Error, in demand units." />
            <MetricCard label="RMSE" value={formatDecimal(data.metrics.rmse)} tooltip="Root Mean Squared Error, in demand units — penalizes large misses more than MAE." />
            <MetricCard label="WAPE" value={formatPercent(data.metrics.wape)} tooltip="Weighted Absolute Percentage Error — lower is better." />
            <MetricCard
              label="MASE"
              value={formatCV(data.metrics.mase)}
              tooltip="Mean Absolute Scaled Error — below 1 means the model beats a naive one-step-ahead baseline."
            />
          </div>

          <Card title="Residual Diagnostics" subtitle={`Model: ${data.model} · ${data.residual_diagnostics.n_residuals} backtest residuals`}>
            <div className={styles.residualRow}>
              <span className={styles.residualLabel}>Mean residual</span>
              <span className={styles.residualValue}>{formatDecimal(data.residual_diagnostics.mean_residual)}</span>
            </div>
            <div className={styles.residualRow}>
              <span className={styles.residualLabel}>Residual std. deviation</span>
              <span className={styles.residualValue}>{formatDecimal(data.residual_diagnostics.std_residual)}</span>
            </div>
            <div className={styles.residualRow}>
              <span className={styles.residualLabel}>Days underpredicted</span>
              <span className={styles.residualValue}>{formatPercent(data.residual_diagnostics.pct_days_underpredicted)}</span>
            </div>
            <div className={styles.residualRow}>
              <span className={styles.residualLabel}>Days overpredicted</span>
              <span className={styles.residualValue}>{formatPercent(data.residual_diagnostics.pct_days_overpredicted)}</span>
            </div>
            {data.residual_diagnostics.ljung_box && (
              <div className={styles.residualRow}>
                <span className={styles.residualLabel}>Autocorrelation (Ljung-Box, {data.residual_diagnostics.ljung_box.lags} lags)</span>
                <Badge variant={getAutocorrelationDisplay(data.residual_diagnostics.ljung_box.autocorrelation_detected).variant}>
                  {getAutocorrelationDisplay(data.residual_diagnostics.ljung_box.autocorrelation_detected).label} (
                  {formatPValue(data.residual_diagnostics.ljung_box.lb_pvalue)})
                </Badge>
              </div>
            )}
            {data.residual_diagnostics.interpretation && (
              <p className={styles.interpretationNote}>{data.residual_diagnostics.interpretation}</p>
            )}
          </Card>

          {data.performance_by_horizon_step.length > 0 && (
            <Table
              caption="Backtest mean absolute error by forecast horizon step"
              columns={horizonColumns}
              rows={data.performance_by_horizon_step}
              rowKey={(row) => String(row.horizon_step)}
              density="compact"
            />
          )}

          {data.limitations.length > 0 && (
            <Card title="Limitations">
              <ul className={styles.limitationsList}>
                {data.limitations.map((limitation) => (
                  <li key={limitation}>{limitation}</li>
                ))}
              </ul>
            </Card>
          )}
        </>
      )}
    </section>
  );
}
