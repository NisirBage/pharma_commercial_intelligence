from pydantic import BaseModel


class FileSummary(BaseModel):
    file_name: str
    total_records: int
    valid_records: int
    rejected_records: int


class ReconciliationStatus(BaseModel):
    label: str  # "Daily" / "Weekly" / "Monthly"
    reconciled: bool
    status: str  # pass / warn / fail
    note: str


class DataQualityResponse(BaseModel):
    kaggle_dataset_id: str
    overall_status: str
    file_summaries: list[FileSummary]
    reconciliation: list[ReconciliationStatus]
    monthly_inconsistency_warning: str
