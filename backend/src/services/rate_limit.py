# Rate limiter — login brute-force protection
#
# In-memory implementation (development/self-hosted-small).
# Production'da Redis-backed rate limiting ile değiştirilir.
# Plan v9 referansı: Bölüm 1.8.2 (Parola Güvenliği)

from __future__ import annotations

import time
from collections import defaultdict
from dataclasses import dataclass, field

import structlog

logger = structlog.get_logger("nova_braille.rate_limit")

# Konfigürasyon
MAX_FAILURES = 5  # Başarısız deneme limiti
LOCK_DURATION = 900  # Kilit süresi (saniye) — 15 dakika
WINDOW = 300  # Deneme penceresi (saniye) — 5 dakika


@dataclass
class _Attempt:
    timestamps: list[float] = field(default_factory=list)
    failures: int = 0
    locked_until: float = 0


class RateLimiter:
    """In-memory rate limiter — email + IP bazlı."""

    def __init__(self) -> None:
        self._by_email: dict[str, _Attempt] = defaultdict(_Attempt)
        self._by_ip: dict[str, _Attempt] = defaultdict(_Attempt)

    def is_locked(self, email: str, ip: str | None = None) -> bool:
        """Kullanıcının email veya IP'si kilitli mi?"""
        now = time.monotonic()
        self._prune(email, ip)

        e = self._by_email.get(email)
        if e and e.locked_until > now:
            return True

        if ip:
            i = self._by_ip.get(ip)
            if i and i.locked_until > now:
                return True

        return False

    def record_failure(self, email: str, ip: str | None = None) -> None:
        """Başarısız giriş denemesini kaydeder."""
        now = time.monotonic()
        self._prune(email, ip)

        # Email bazlı takip
        e = self._by_email[email]
        e.timestamps.append(now)
        e.failures += 1

        if e.failures >= MAX_FAILURES:
            e.locked_until = now + LOCK_DURATION
            logger.warning(
                "account_locked_email",
                email=email[:3] + "***",  # PII minimizasyonu
                failures=e.failures,
                locked_seconds=LOCK_DURATION,
            )

        # IP bazlı takip
        if ip:
            i = self._by_ip[ip]
            i.timestamps.append(now)
            i.failures += 1
            if i.failures >= MAX_FAILURES:
                i.locked_until = now + LOCK_DURATION
                logger.warning(
                    "account_locked_ip",
                    ip=ip[:4] + "***",
                    failures=i.failures,
                )

    def record_success(self, email: str, ip: str | None = None) -> None:
        """Başarılı giriş sonrası sayaçları sıfırlar."""
        if email in self._by_email:
            del self._by_email[email]
        if ip and ip in self._by_ip:
            del self._by_ip[ip]

    def _prune(self, email: str, ip: str | None = None) -> None:
        """Pencere dışındaki eski denemeleri temizler."""
        now = time.monotonic()
        cutoff = now - WINDOW

        e = self._by_email.get(email)
        if e:
            # Kilit süresi doldu mu?
            if e.locked_until and e.locked_until <= now:
                e.locked_until = 0
                e.failures = 0
                e.timestamps.clear()
            else:
                # Pencere dışı kayıtları temizle
                e.timestamps = [t for t in e.timestamps if t > cutoff]
                e.failures = len(e.timestamps)

        if ip:
            i = self._by_ip.get(ip)
            if i:
                if i.locked_until and i.locked_until <= now:
                    i.locked_until = 0
                    i.failures = 0
                    i.timestamps.clear()
                else:
                    i.timestamps = [t for t in i.timestamps if t > cutoff]
                    i.failures = len(i.timestamps)


# Singleton
rate_limiter = RateLimiter()