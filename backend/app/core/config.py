"""Application configuration, read from environment / .env — no hard-coded
machine-specific paths so the pipeline is reproducible on another machine."""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
PROJECT_ROOT = BACKEND_DIR.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=str(PROJECT_ROOT / ".env"), extra="ignore")

    # Postgres connection. Individual POSTGRES_* values are combined into
    # DATABASE_URL if DATABASE_URL itself isn't set explicitly.
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "pharma_ci"
    postgres_user: str = "pharma_ci"
    postgres_password: str = "changeme"
    database_url: str | None = None

    # Where the raw Kaggle CSVs live (populated by scripts/download_data.py).
    raw_data_dir: Path = PROJECT_ROOT / "data" / "raw"

    # Where machine-readable data-quality reports are written.
    quality_report_dir: Path = BACKEND_DIR / "data" / "quality_reports"

    kaggle_dataset_id: str = "milanzdravkovic/pharma-sales-data"

    @property
    def sqlalchemy_database_url(self) -> str:
        if self.database_url:
            return self.database_url
        return (
            f"postgresql+psycopg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


settings = Settings()
