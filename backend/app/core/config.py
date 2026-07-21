"""Environment-based application configuration.

All settings are loaded from environment variables (or a local, gitignored ``.env``).
Nothing sensitive is hardcoded. See ``.env.example`` for the full list.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# backend/ directory (two levels up from this file: app/core/config.py -> backend/)
BACKEND_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """Strongly-typed application settings."""

    model_config = SettingsConfigDict(
        env_file=(BACKEND_DIR / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ---- Application ----
    app_name: str = "AgentCare"
    environment: str = "development"
    debug: bool = True
    api_v1_prefix: str = "/api/v1"
    backend_cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"

    # ---- Security ----
    secret_key: str = "insecure-dev-key-change-me"
    access_token_expire_minutes: int = 720
    jwt_algorithm: str = "HS256"

    # ---- Database ----
    database_url: str = f"sqlite:///{(BACKEND_DIR / 'agentcare.db').as_posix()}"

    # ---- LLM / Agents ----
    llm_provider: str = "anthropic"  # anthropic | mock
    anthropic_api_key: str = ""
    llm_model: str = "claude-sonnet-5"
    llm_temperature: float = 0.0
    llm_max_tokens: int = 1024
    llm_max_retries: int = 3

    # ---- Document storage ----
    storage_dir: str = str(BACKEND_DIR / "storage")
    max_upload_mb: int = 15

    # ---- Seed ----
    seed_default_password: str = "AgentCare!2026"

    # ---- Startup behaviour ----
    # Create any missing tables on startup (dev convenience; production uses Alembic).
    auto_init_db: bool = True
    # Seed synthetic data on startup if the database is empty.
    auto_seed: bool = True
    # Also run a few demo requests through the real agent graph so the app/analytics
    # look populated on first load. Disabled in tests for determinism.
    seed_demo_workflows: bool = True

    @field_validator("database_url")
    @classmethod
    def _normalize_db_url(cls, v: str) -> str:
        # Managed Postgres providers (Render/Heroku/Railway) hand out `postgres://...`,
        # which SQLAlchemy 2.0 no longer accepts. Normalize to the psycopg2 driver.
        if v.startswith("postgres://"):
            return "postgresql+psycopg2://" + v[len("postgres://"):]
        if v.startswith("postgresql://") and "+psycopg" not in v:
            return "postgresql+psycopg2://" + v[len("postgresql://"):]
        return v

    @field_validator("backend_cors_origins")
    @classmethod
    def _strip_origins(cls, v: str) -> str:
        return v.strip()

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.backend_cors_origins.split(",") if o.strip()]

    @property
    def storage_path(self) -> Path:
        p = Path(self.storage_dir)
        if not p.is_absolute():
            p = BACKEND_DIR / p
        return p

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")

    @property
    def use_real_llm(self) -> bool:
        """Whether a genuine LLM call should be attempted.

        Falls back to the deterministic mock provider when explicitly configured
        or when no Anthropic key is present, so the app still runs offline/in CI.
        """
        return self.llm_provider.lower() == "anthropic" and bool(self.anthropic_api_key)


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
