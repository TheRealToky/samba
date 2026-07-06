"""Application settings.

Values can be overridden via a `.env` file (see .env.example) or environment
variables prefixed with `SAMBA_`. Sane dev defaults let the app run with zero config.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="SAMBA_", extra="ignore")

    secret_key: str = "dev-secret-change-me-in-production-0123456789"
    database_url: str = "sqlite:///./samba.db"
    access_token_expire_minutes: int = 60 * 12  # 12h

    # Rule-based detector knobs (stand-in for the future ML pipeline).
    ndvi_drop_threshold_pct: float = 25.0
    detection_window_days: int = 60

    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
