"""Import every model so app.db.base.Base.metadata is complete for Alembic
autogenerate and for tests that call Base.metadata.create_all()."""

from app.models.atc_class import AtcClass
from app.models.etl_run import DataQualityCheck, EtlRun
from app.models.fact import FactDemandHourly
from app.models.staging import StgSalesDaily, StgSalesHourly, StgSalesMonthly, StgSalesWeekly

__all__ = [
    "AtcClass",
    "DataQualityCheck",
    "EtlRun",
    "FactDemandHourly",
    "StgSalesDaily",
    "StgSalesHourly",
    "StgSalesMonthly",
    "StgSalesWeekly",
]
