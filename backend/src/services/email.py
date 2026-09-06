# Email service — SMTP delivery with Jinja2 templates and Dramatiq worker
#
# Hosted mod: kadirunver@gorbil.com SMTP (my.mailbux.com:587 STARTTLS)
# Self-hosted mod: kullanıcının kendi SMTP ayarları
# Plan v9 referansı: Bölüm 1.3, 1.5.2

from __future__ import annotations

from email.message import EmailMessage
from pathlib import Path
from typing import Protocol

import structlog
from jinja2 import Environment, FileSystemLoader

from ..config import settings

logger = structlog.get_logger("nova_braille.email")

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "email" / "templates"


class EmailSender(Protocol):
    """SMTP gönderim protokolü — test edilebilirlik için."""

    async def __call__(self, msg: EmailMessage) -> None: ...


class SmtpSender:
    """Gerçek SMTP gönderici."""

    async def __call__(self, msg: EmailMessage) -> None:
        import aiosmtplib

        await aiosmtplib.send(
            msg,
            hostname=settings.smtp_host,
            port=settings.smtp_port,
            username=settings.smtp_user,
            password=settings.smtp_password,
            start_tls=settings.smtp_use_tls,
        )


class EmailService:
    """E-posta gönderim servisi.

    - Hosted mod: Gerçek SMTP (my.mailbux.com) + Dramatiq kuyruk
    - Self-hosted mod: Kullanıcının SMTP ayarları
    - Geliştirme: Log'a yazar, SMTP çağrılmaz
    """

    def __init__(self, sender: EmailSender | None = None) -> None:
        self._env = Environment(
            loader=FileSystemLoader(str(TEMPLATES_DIR)),
            autoescape=False,  # Plain text emails
        )
        self._sender = sender or SmtpSender()

    # ---------- Public API ----------

    async def send_activation(
        self,
        email: str,
        activation_url: str,
        display_name: str | None = None,
    ) -> None:
        await self._send_template(
            to=email,
            template="activation.txt.jinja2",
            subject="Nova Braille — Hesabınızı Etkinleştirin",
            activation_url=activation_url,
            display_name=display_name,
        )

    async def send_password_reset(
        self,
        email: str,
        reset_url: str,
        display_name: str | None = None,
    ) -> None:
        await self._send_template(
            to=email,
            template="password_reset.txt.jinja2",
            subject="Nova Braille — Parola Sıfırlama",
            reset_url=reset_url,
            display_name=display_name,
        )

    # ---------- Internal ----------

    async def _send_template(
        self, to: str, template: str, subject: str, **ctx
    ) -> None:
        """Jinja2 şablonu render eder ve gönderir."""
        try:
            tmpl = self._env.get_template(template)
            body = tmpl.render(**ctx)

            msg = EmailMessage()
            msg["From"] = settings.smtp_from
            msg["To"] = to
            msg["Subject"] = subject
            msg.set_content(body, subtype="plain", charset="utf-8")

            if settings.is_development:
                logger.info(
                    "email.development",
                    to=to,
                    subject=subject,
                )
                return

            await self._sender(msg)
            logger.info("email.sent", to=_mask(to), subject=subject)

        except Exception:
            logger.error("email.failed", to=_mask(to), subject=subject, exc_info=True)
            raise


# ---------- Dramatiq worker ----------

async def enqueue_email(**kwargs) -> None:
    """E-postayı Dramatiq kuyruğuna ekler.

    Redis yoksa doğrudan gönderir (development/small self-hosted).
    """
    if not settings.redis_url:
        # Sync gönderim — development
        await email_service._send_template(**kwargs)  # noqa: SLF001
        return

    import dramatiq

    @dramatiq.actor(queue_name="email")
    async def _send_email(**kw):
        await email_service._send_template(**kw)  # noqa: SLF001

    _send_email.send(**kwargs)


# ---------- Helpers ----------

def _mask(email: str) -> str:
    if "@" not in email:
        return "***"
    local, domain = email.split("@", 1)
    return f"{local[:2]}***@{domain}"


# Singleton
email_service = EmailService()