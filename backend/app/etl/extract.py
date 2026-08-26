"""Extraction: read the 4 raw CSVs exactly as downloaded. No cleaning,
filtering, or interpretation happens here — that's validate.py/transform.py.
The raw files themselves are never modified (immutable source of truth)."""

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from app.core.config import settings

EXPECTED_FILES = ("saleshourly.csv", "salesdaily.csv", "salesweekly.csv", "salesmonthly.csv")

# Date format differs per file (see docs/01-data-dictionary.md) — must be
# handled explicitly, never inferred, to avoid silent misparsing.
DATE_FORMATS = {
    "saleshourly.csv": "%m/%d/%Y %H:%M",
    "salesdaily.csv": "%m/%d/%Y",
    "salesweekly.csv": "%m/%d/%Y",
    "salesmonthly.csv": "%Y-%m-%d",
}


@dataclass
class RawDataset:
    name: str
    path: Path
    frame: pd.DataFrame


def extract_all(raw_data_dir: Path | None = None) -> dict[str, RawDataset]:
    raw_data_dir = raw_data_dir or settings.raw_data_dir
    datasets: dict[str, RawDataset] = {}
    missing = []
    for filename in EXPECTED_FILES:
        path = raw_data_dir / filename
        if not path.exists():
            missing.append(str(path))
            continue
        frame = pd.read_csv(path)
        datasets[filename] = RawDataset(name=filename, path=path, frame=frame)

    if missing:
        raise FileNotFoundError(
            "Missing expected raw source file(s): "
            + ", ".join(missing)
            + ". Run scripts/download_data.py first."
        )
    return datasets
