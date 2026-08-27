from pydantic import BaseModel

from app.schemas.common import SafeFloat


class ForecastPoint(BaseModel):
    date: str
    prediction: SafeFloat
    lower: SafeFloat
    upper: SafeFloat


class ForecastMetrics(BaseModel):
    mae: SafeFloat
    rmse: SafeFloat
    wape: SafeFloat
    mase: SafeFloat


class ForecastResponse(BaseModel):
    atc_class: str
    horizon_days: int
    model: str
    uncertainty_method: str
    forecast: list[ForecastPoint]
    metrics: ForecastMetrics


class LjungBoxResult(BaseModel):
    lags: int
    lb_stat: SafeFloat
    lb_pvalue: SafeFloat
    autocorrelation_detected: bool


class ResidualDiagnostics(BaseModel):
    n_residuals: int
    mean_residual: SafeFloat
    std_residual: SafeFloat
    pct_days_underpredicted: SafeFloat
    pct_days_overpredicted: SafeFloat
    ljung_box: LjungBoxResult | None
    interpretation: str


class HorizonStepError(BaseModel):
    horizon_step: int
    mae: SafeFloat
    n_observations: int


class ForecastDiagnosticsResponse(BaseModel):
    atc_class: str
    model: str
    metrics: ForecastMetrics
    residual_diagnostics: ResidualDiagnostics
    performance_by_horizon_step: list[HorizonStepError]
    limitations: list[str]
