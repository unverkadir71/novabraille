# SmtpConfig model — single-row SMTP configuration (ADR-023)
#
# Admin panelinden SMTP ayarlarını görüntüleme, düzenleme, etkinleştirme/devre dışı bırakma.
# Şifre alanı AES (Fernet) ile şifrelenir, API yanıtında maskeli döner.

from __future__ import annotations

from sqlalchemy import Boolean, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class SmtpConfig(Base):
    __tablename__ = "smtp_config"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    enabled: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0")
    host: Mapped[str] = mapped_column(String(255), default="localhost", server_default="localhost")
    port: Mapped[int] = mapped_column(Integer, default=587, server_default="587")
    username: Mapped[str] = mapped_column(String(255), default="", server_default="")
    password_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    from_name: Mapped[str] = mapped_column(String(100), default="Nova Braille", server_default="Nova Braille")
    from_email: Mapped[str] = mapped_column(String(254), default="noreply@novabraille.example.com", server_default="noreply@novabraille.example.com")
    use_tls: Mapped[bool] = mapped_column(Boolean, default=True, server_default="1")

    def __repr__(self) -> str:
        return f"<SmtpConfig(enabled={self.enabled}, host={self.host!r})>"
