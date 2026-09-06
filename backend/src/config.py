# Pydantic Settings based application configuration
#
# Reads from environment variables and .env files.
# Plan v9 referansı: Bölüm 1.5 (Hosted/Self-hosted Modları), 1.13 (Teknik Mimari)

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Application mode: development | hosted | self_hosted
    app_mode: str = "development"

    # Database — async URL
    database_url: str = "sqlite+aiosqlite:///./nova-braille.db"

    # Security
    secret_key: str = "change-me-in-production-use-openssl-rand-hex-32"

    # SMTP
    smtp_host: str = "localhost"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = "noreply@novabraille.example.com"
    smtp_use_tls: bool = True

    # Redis (opsiyonel — Dramatiq worker + rate limit)
    redis_url: str = ""

    # Self-hosted settings
    self_hosted_registration: str = "closed"  # open | closed
    self_hosted_char_limit: int = 0  # 0 = sınırsız

    # Admin bootstrap (self-hosted — ADR-022)
    nova_admin_email: str = ""
    nova_admin_password: str = ""

    # Billing (hosted only)
    billing_provider: str = ""

    # Liblouis table directory (default: system install)
    liblouis_table_dir: str = ""

    # Translation limits
    max_translation_chars: int = 500_000  # Tek istekte max karakter
    translation_timeout_seconds: int = 30  # Çeviri işlemi timeout (saniye)
    max_file_upload_bytes: int = 50 * 1024 * 1024  # 50 MB

    # TZ
    tz: str = "Europe/Istanbul"

    # Logging
    log_level: str = "info"

    # Monitoring (opsiyonel)
    sentry_dsn: str = ""

    # Application URL (for email links)
    app_url: str = "http://localhost:9876"

    @property
    def is_development(self) -> bool:
        return self.app_mode == "development"

    @property
    def is_hosted(self) -> bool:
        return self.app_mode == "hosted"

    @property
    def is_self_hosted(self) -> bool:
        return self.app_mode == "self_hosted"


settings = Settings()