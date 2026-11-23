"""Centralised configuration for the AIPlanX API.

Everything the API needs to run (auth, AI, email, storage) is resolved here so
route modules never read raw environment variables or hold secrets.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")


def _env(name: str, default: str | None = None) -> str | None:
    value = os.getenv(name)
    if value is None:
        return default
    stripped = value.strip()
    return stripped or default


def _truthy(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _path_env(name: str, default: Path) -> Path:
    raw = _env(name)
    path = Path(raw) if raw else default
    return path if path.is_absolute() else ROOT / path


class ConfigurationError(RuntimeError):
    """Raised when required configuration is missing or contradictory."""


@dataclass(frozen=True)
class AuthSettings:
    provider: str
    supabase_url: str | None = None
    supabase_jwks_url: str | None = None
    supabase_jwt_secret: str | None = None
    supabase_jwt_audience: str | None = "authenticated"
    supabase_service_role_key: str | None = None
    dev_allowed: bool = False
    dev_secret: str = "aiplanx-local-dev-secret"

    @property
    def is_supabase(self) -> bool:
        return self.provider == "supabase"


@dataclass(frozen=True)
class AiSettings:
    assistant_api_key: str | None
    assistant_model: str
    insights_api_key: str | None
    insights_model: str
    legacy_groq_key: str | None
    google_api_key: str | None

    @property
    def assistant_configured(self) -> bool:
        return bool(self.assistant_api_key)

    @property
    def insights_configured(self) -> bool:
        return bool(self.insights_api_key)


@dataclass(frozen=True)
class EmailSettings:
    host: str | None
    port: int
    username: str | None
    password: str | None
    sender: str
    use_tls: bool
    frontend_url: str

    @property
    def enabled(self) -> bool:
        return bool(self.host)


@dataclass(frozen=True)
class StorageSettings:
    backend: str
    sqlite_path: Path
    session_dir: Path
    report_path: Path
    employee_path: Path
    team_workflow_path: Path


@dataclass(frozen=True)
class Settings:
    auth: AuthSettings
    ai: AiSettings
    email: EmailSettings
    storage: StorageSettings
    cors_origins: tuple[str, ...] = field(default_factory=tuple)


def _resolve_auth() -> AuthSettings:
    explicit = _env("AUTH_PROVIDER")
    supabase_url = _env("SUPABASE_URL")
    jwks_url = _env("SUPABASE_JWKS_URL")
    if not jwks_url and supabase_url:
        jwks_url = f"{supabase_url.rstrip('/')}/auth/v1/.well-known/jwks.json"

    if explicit:
        provider = explicit.lower()
    elif supabase_url or jwks_url or _env("SUPABASE_JWT_SECRET"):
        provider = "supabase"
    else:
        provider = "dev"

    if provider not in {"supabase", "dev"}:
        raise ConfigurationError(
            f"AUTH_PROVIDER must be 'supabase' or 'dev', got {provider!r}."
        )

    if provider == "supabase" and not (jwks_url or _env("SUPABASE_JWT_SECRET")):
        raise ConfigurationError(
            "Supabase auth requires SUPABASE_URL (to derive JWKS) or "
            "SUPABASE_JWKS_URL or SUPABASE_JWT_SECRET."
        )

    dev_allowed = _truthy(_env("AUTH_ALLOW_DEV_PROVIDER"), default=True)
    if provider == "dev" and not dev_allowed:
        raise ConfigurationError(
            "AUTH_PROVIDER is 'dev' but AUTH_ALLOW_DEV_PROVIDER is disabled."
        )

    return AuthSettings(
        provider=provider,
        supabase_url=supabase_url,
        supabase_jwks_url=jwks_url,
        supabase_jwt_secret=_env("SUPABASE_JWT_SECRET"),
        supabase_jwt_audience=_env("SUPABASE_JWT_AUDIENCE", "authenticated"),
        supabase_service_role_key=_env("SUPABASE_SERVICE_ROLE_KEY"),
        dev_allowed=dev_allowed,
        dev_secret=_env("DEV_AUTH_TOKEN_SECRET", "aiplanx-local-dev-secret"),
    )


def _resolve_ai() -> AiSettings:
    assistant_key = _env("GROQ_API_KEY_1")
    insights_key = assistant_key
    return AiSettings(
        assistant_api_key=assistant_key,
        assistant_model=_env("GROQ_ASSISTANT_MODEL", "openai/gpt-oss-120b"),
        insights_api_key=insights_key,
        insights_model=_env("GROQ_INSIGHTS_MODEL", "openai/gpt-oss-120b"),
        legacy_groq_key=_env("GROQ_API_KEY"),
        google_api_key=_env("GOOGLE_API_KEY"),
    )


def _resolve_email() -> EmailSettings:
    port_raw = _env("SMTP_PORT", "587")
    try:
        port = int(port_raw)
    except ValueError as error:
        raise ConfigurationError(f"SMTP_PORT must be an integer, got {port_raw!r}.") from error
    return EmailSettings(
        host=_env("SMTP_HOST"),
        port=port,
        username=_env("SMTP_USERNAME"),
        password=_env("SMTP_PASSWORD"),
        sender=_env("SMTP_FROM", "AIPlanX <no-reply@aiplanx.local>"),
        use_tls=_truthy(_env("SMTP_USE_TLS"), default=True),
        frontend_url=_env("FRONTEND_URL", "http://localhost:5173").rstrip("/"),
    )


def _resolve_storage() -> StorageSettings:
    return StorageSettings(
        backend=_env("AIPlanX_STORE", "sqlite").lower(),
        sqlite_path=_path_env("SQLITE_PATH", ROOT / "aiplanx.db"),
        session_dir=_path_env("SESSION_DIR", ROOT / "management_sessions"),
        report_path=_path_env("REPORT_PATH", ROOT / "final_report.json"),
        employee_path=_path_env("EMPLOYEE_PATH", ROOT / "employees.csv"),
        team_workflow_path=ROOT / "team_workflow.json",
    )


def _resolve_cors() -> tuple[str, ...]:
    raw = _env("CORS_ORIGINS")
    if raw:
        return tuple(origin.strip() for origin in raw.split(",") if origin.strip())
    return (
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:4173",
        "http://127.0.0.1:4173",
    )


def load_settings() -> Settings:
    storage = _resolve_storage()
    return Settings(
        auth=_resolve_auth(),
        ai=_resolve_ai(),
        email=_resolve_email(),
        storage=storage,
        cors_origins=_resolve_cors(),
    )


_settings_cache: Settings | None = None


def get_settings() -> Settings:
    global _settings_cache
    if _settings_cache is None:
        _settings_cache = load_settings()
    return _settings_cache


def reset_settings_cache() -> None:
    """Test helper: drop the memoized settings so env changes take effect."""
    global _settings_cache
    _settings_cache = None


__all__ = [
    "AiSettings",
    "AuthSettings",
    "ConfigurationError",
    "EmailSettings",
    "Settings",
    "StorageSettings",
    "ROOT",
    "get_settings",
    "load_settings",
    "reset_settings_cache",
]