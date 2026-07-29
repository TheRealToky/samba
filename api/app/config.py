"""Application settings, loaded from environment (see .env.example)."""
from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", case_sensitive=False)

    # Database
    database_url: str = "postgresql+psycopg://samba:samba_dev_password@localhost:5432/samba"

    # Auth (NFR-1)
    jwt_secret: str = "dev-only-change-me"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    # Queue / storage / inference (used from Phase 2 onward)
    redis_url: str = "redis://localhost:6379/0"
    minio_endpoint: str = "localhost:9000"
    minio_root_user: str = "samba"
    minio_root_password: str = "samba_dev_password"
    minio_bucket: str = "samba"
    inference_url: str = "http://localhost:9000"

    # External providers (Phase 2)
    gee_service_account_json: str = ""
    gee_project: str = ""
    # "sample" = deterministic synthetic data (no network/creds); "live" = real APIs.
    ingestion_mode: str = "sample"
    # Per-source overrides (None = fall back to ingestion_mode). Lets the auth-free
    # sources (climate/biodiversity) run live while satellite stays on sample until
    # Earth Engine credentials are configured.
    ingestion_mode_satellite: str | None = None
    ingestion_mode_climate: str | None = None
    ingestion_mode_biodiversity: str | None = None
    # Max occurrences to pull per region per run in live biodiversity ingestion.
    biodiversity_max_records: int = 500

    # ML (Phase 3)
    model_dir: str = "/models"

    app_name: str = "SAMBA API"
    app_version: str = "0.1.0"


settings = Settings()
