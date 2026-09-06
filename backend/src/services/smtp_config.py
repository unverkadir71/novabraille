# SmtpConfig service — SMTP ayarları CRUD + Fernet şifreleme (ADR-023)
#
# SmtpConfig tek satırlı modeldir (id=1). GET/PUT ile yönetilir.
# SMTP şifresi Fernet (AES-128-CBC + HMAC-SHA256) ile şifrelenir.
# API yanıtında şifre maskeli (***) döner.

from __future__ import annotations

import base64
from typing import Any

from cryptography.fernet import Fernet
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..models.smtp_config import SmtpConfig


class SmtpConfigService:
    """SMTP yapılandırması yönetim servisi."""

    def __init__(self) -> None:
        # Fernet anahtarı config'teki secret_key'ten türetilir
        key = base64.urlsafe_b64encode(
            settings.secret_key.encode()[:32].ljust(32, b"\x00")
        )
        self._fernet = Fernet(key)

    def _encrypt(self, plaintext: str) -> str:
        """Düz metni Fernet ile şifreler, base64 string döner."""
        if not plaintext:
            return None
        return self._fernet.encrypt(plaintext.encode()).decode()

    def _decrypt(self, ciphertext: str | None) -> str | None:
        """Şifreli metni çözer. None veya hatalı veride None döner."""
        if not ciphertext:
            return None
        try:
            return self._fernet.decrypt(ciphertext.encode()).decode()
        except Exception:
            return None

    async def get_config(self, db: AsyncSession) -> SmtpConfig | None:
        """SMTP yapılandırmasını döndürür. Yoksa None."""
        result = await db.execute(
            select(SmtpConfig).where(SmtpConfig.id == 1)
        )
        return result.scalar_one_or_none()

    async def get_or_create(self, db: AsyncSession) -> SmtpConfig:
        """SMTP yapılandırmasını döndürür, yoksa varsayılan oluşturur."""
        config = await self.get_config(db)
        if config is None:
            config = SmtpConfig(id=1)
            db.add(config)
            await db.flush()
        return config

    async def update_config(
        self, db: AsyncSession, data: dict[str, Any]
    ) -> SmtpConfig:
        """SMTP yapılandırmasını günceller.

        Beklenen alanlar: enabled, host, port, username, password (düz metin),
        from_name, from_email, use_tls.
        """
        config = await self.get_or_create(db)

        if "enabled" in data:
            config.enabled = bool(data["enabled"])
        if "host" in data:
            config.host = str(data["host"])
        if "port" in data:
            config.port = int(data["port"])
        if "username" in data:
            config.username = str(data["username"])
        if "password" in data and data["password"] is not None:
            pw = str(data["password"])
            if pw:  # yalnızca boş değilse güncelle, boşsa mevcut korunur
                config.password_encrypted = self._encrypt(pw)
        if "from_name" in data:
            config.from_name = str(data["from_name"])
        if "from_email" in data:
            config.from_email = str(data["from_email"])
        if "use_tls" in data:
            config.use_tls = bool(data["use_tls"])

        await db.flush()
        return config

    def to_api_response(self, config: SmtpConfig) -> dict:
        """API yanıtı için güvenli (şifresiz) dict üretir."""
        has_password = bool(
            config.password_encrypted and self._decrypt(config.password_encrypted)
        )
        return {
            "enabled": config.enabled,
            "host": config.host,
            "port": config.port,
            "username": config.username,
            "password_set": has_password,
            "from_name": config.from_name,
            "from_email": config.from_email,
            "use_tls": config.use_tls,
        }

    async def send_test_email(self, config: SmtpConfig) -> dict:
        """SMTP ayarlarıyla test e-postası gönderir."""
        import aiosmtplib
        from email.message import EmailMessage

        password = self._decrypt(config.password_encrypted) or ""

        msg = EmailMessage()
        msg["From"] = f"{config.from_name} <{config.from_email}>"
        msg["To"] = config.from_email
        msg["Subject"] = "Nova Braille — SMTP Test E-postası"
        msg.set_content(
            "Bu bir test e-postasıdır. SMTP ayarlarınız başarıyla yapılandırıldı.",
            subtype="plain",
            charset="utf-8",
        )

        try:
            await aiosmtplib.send(
                msg,
                hostname=config.host,
                port=config.port,
                username=config.username or None,
                password=password or None,
                start_tls=config.use_tls,
                timeout=15,
            )
            return {"success": True, "message": "Test e-postası başarıyla gönderildi."}
        except Exception as e:
            return {"success": False, "message": f"Gönderim başarısız: {str(e)}"}

    def get_smtp_settings(self, config: SmtpConfig) -> dict:
        """EmailService tarafından kullanılabilecek SMTP ayarlarını döndürür."""
        password = self._decrypt(config.password_encrypted) or ""
        return {
            "host": config.host,
            "port": config.port,
            "username": config.username,
            "password": password,
            "from_email": config.from_email,
            "from_name": config.from_name,
            "use_tls": config.use_tls,
        }


# Singleton
smtp_config_service = SmtpConfigService()
