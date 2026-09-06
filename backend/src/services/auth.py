# Auth service — password hashing and verification
#
# Uses pwdlib with Argon2id (OWASP 2026 birincil önerisi).
# Plan v9 referansı: Bölüm 1.8.2 (Parola Güvenliği), 1.13.1 (pwdlib[argon2])

from __future__ import annotations

from pwdlib import PasswordHash
from pwdlib.hashers.argon2 import Argon2Hasher


class AuthService:
    """Parola hashleme ve doğrulama servisi.

    Argon2id parametreleri (OWASP 2026 minimum):
    - memory_cost: 65536 KB (64 MB)
    - time_cost: 3 iteration
    - parallelism: 4 thread
    - hash_len: 32 byte
    - salt_len: 16 byte
    """

    def __init__(self) -> None:
        self._hasher = PasswordHash(
            [
                Argon2Hasher(
                    memory_cost=65536,
                    time_cost=3,
                    parallelism=4,
                    hash_len=32,
                    salt_len=16,
                )
            ]
        )

    def hash_password(self, password: str) -> str:
        """Düz metin parolayı Argon2id ile hash'ler.

        Parola uzunluğu min 8, max 128 karakter olmalıdır.
        Validasyon çağrı öncesinde schema katmanında yapılır.
        """
        return self._hasher.hash(password)

    def verify_password(self, password: str, password_hash: str) -> bool:
        """Düz metin parolayı hash ile karşılaştırır. Sabit zamanlıdır."""
        try:
            return self._hasher.verify(password, password_hash)
        except Exception:
            # Bilinmeyen hash formatı → yanlış parola gibi davran
            return False

    @staticmethod
    def is_weak_password(password: str) -> bool:
        """Zayıf parola kontrolü. True = zayıf, reddedilmeli."""
        return len(password) < 8 or len(password) > 128


# Singleton — servis katmanında doğrudan import edilebilir
auth_service = AuthService()