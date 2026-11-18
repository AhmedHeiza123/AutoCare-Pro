from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="AUTOCARE_", env_file=BACKEND_DIR / ".env", extra="ignore"
    )

    database_url: str
    secret_key: str = Field(min_length=24)
    session_minutes: int = 480
    max_failed_logins: int = 5
    lockout_minutes: int = 15
    cookie_secure: bool = False  # set True when served over HTTPS
    storage_dir: Path = BACKEND_DIR / "storage"
    pg_bin_dir: Path | None = None  # folder containing pg_dump / pg_restore (auto-detected when empty)
    disable_scheduler: bool = False
    host: str = "127.0.0.1"  # 0.0.0.0 = local network mode
    port: int = 8000
    ssl_certfile: str | None = None
    ssl_keyfile: str | None = None

    @field_validator("secret_key")
    @classmethod
    def _not_placeholder(cls, v: str) -> str:
        if v.startswith("CHANGE_ME"):
            raise ValueError("AUTOCARE_SECRET_KEY must be set to a real random value")
        return v


@lru_cache
def get_settings() -> Settings:
    return Settings()
