"""Download the source dataset via kagglehub and copy it into data/raw/.

Usage:
    python scripts/download_data.py

Requires a Kaggle API token at ~/.kaggle/kaggle.json (or KAGGLE_USERNAME /
KAGGLE_KEY env vars) — see https://www.kaggle.com/docs/api for how to
generate one. This script does not fabricate or fall back to sample data:
if the download fails, it fails loudly.
"""

import shutil
from pathlib import Path

import kagglehub

DATASET = "milanzdravkovic/pharma-sales-data"
RAW_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"


def main() -> None:
    print(f"Downloading {DATASET} via kagglehub ...")
    cache_path = Path(kagglehub.dataset_download(DATASET))
    print(f"kagglehub cached the dataset at: {cache_path}")

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    copied = []
    for item in cache_path.iterdir():
        dest = RAW_DIR / item.name
        if item.is_dir():
            shutil.copytree(item, dest, dirs_exist_ok=True)
        else:
            shutil.copy2(item, dest)
        copied.append(dest.name)

    print(f"Copied {len(copied)} item(s) into {RAW_DIR}:")
    for name in copied:
        print(f"  - {name}")


if __name__ == "__main__":
    main()
