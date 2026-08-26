"""Print the actual schema of every raw CSV: columns, dtypes, shape, nulls, sample rows.

Ground truth for docs/02-data-dictionary.md — never write that doc from memory
or assumption, always regenerate this output and transcribe from it.
"""

from pathlib import Path

import pandas as pd

RAW_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"


def inspect(path: Path) -> None:
    df = pd.read_csv(path)
    print("=" * 100)
    print(f"FILE: {path.name}")
    print(f"shape: {df.shape}")
    print("-" * 100)
    print("dtypes:")
    print(df.dtypes)
    print("-" * 100)
    print("null counts:")
    print(df.isnull().sum())
    print("-" * 100)
    print("first 3 rows:")
    print(df.head(3).to_string())
    print("-" * 100)
    print("last 3 rows:")
    print(df.tail(3).to_string())
    print()


def main() -> None:
    files = sorted(RAW_DIR.glob("*.csv"))
    if not files:
        raise SystemExit(f"No CSVs found in {RAW_DIR}. Run scripts/download_data.py first.")
    for f in files:
        inspect(f)


if __name__ == "__main__":
    main()
