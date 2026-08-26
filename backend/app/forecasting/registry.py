"""Lightweight, file-based model metadata registry. No MLflow — per M4
Sec. 15 ("do not introduce MLflow unless genuinely useful"), a single JSON
file per trained model is sufficient at this project's scale and is
trivially reproducible/diffable in version control.
"""

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from app.core.config import settings

REGISTRY_DIR = settings.quality_report_dir.parent / "model_registry"
RAW_FILES = ("saleshourly.csv", "salesdaily.csv", "salesweekly.csv", "salesmonthly.csv")


@dataclass
class ModelRecord:
    model_name: str
    atc_class: str
    training_period: str
    validation_period: str
    forecast_horizon: int
    features: list[str]
    hyperparameters: dict
    evaluation_metrics: dict
    trained_at: str
    dataset_version_hash: str


def dataset_version_hash(raw_data_dir: Path) -> str:
    """A reproducible proxy for "dataset version" — the Kaggle dataset has
    no formal version field (M1), so this hashes each raw file's row
    count, columns, and first/last row, which changes if and only if the
    underlying data actually changes."""
    parts = []
    for name in RAW_FILES:
        path = raw_data_dir / name
        if not path.exists():
            continue
        df = pd.read_csv(path)
        parts.append(f"{name}:{len(df)}:{list(df.columns)}:{df.iloc[0].to_dict()}:{df.iloc[-1].to_dict()}")
    return hashlib.sha256("|".join(parts).encode()).hexdigest()[:16]


def save_record(record: ModelRecord, registry_dir: Path = REGISTRY_DIR) -> Path:
    registry_dir.mkdir(parents=True, exist_ok=True)
    path = registry_dir / f"{record.atc_class}_{record.model_name}.json"
    path.write_text(json.dumps(asdict(record), indent=2), encoding="utf-8")
    return path


def load_registry(registry_dir: Path = REGISTRY_DIR) -> list[dict]:
    if not registry_dir.exists():
        return []
    return [json.loads(p.read_text(encoding="utf-8")) for p in sorted(registry_dir.glob("*.json"))]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
