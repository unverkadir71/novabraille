# Account schemas — Pydantic v2 models for account update (ADR-021)
#
# Hosted ve self-hosted tüm kullanıcılar display_name, email, password değiştirebilir.
# Kısmi güncelleme (PATCH) — sadece gönderilen alanlar güncellenir.

from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field, model_validator


class AccountUpdate(BaseModel):
    """Hesap bilgileri kısmi güncelleme isteği.

    Tüm alanlar isteğe bağlıdır — yalnızca gönderilenler güncellenir.
    Parola değişikliği için current_password zorunludur.
    """

    display_name: str | None = Field(
        None,
        min_length=1,
        max_length=100,
        description="Yeni görünen ad",
    )
    email: EmailStr | None = Field(
        None,
        description="Yeni e-posta adresi",
    )
    new_password: str | None = Field(
        None,
        min_length=8,
        max_length=128,
        description="Yeni parola (en az 8 karakter)",
    )
    current_password: str = Field(
        ...,
        min_length=1,
        description="Mevcut parola — tüm değişiklikler için zorunlu",
    )

    @model_validator(mode="after")
    def check_at_least_one_change(self) -> "AccountUpdate":
        """En az bir değişiklik alanı gönderilmelidir."""
        if (
            self.display_name is None
            and self.email is None
            and self.new_password is None
        ):
            raise ValueError(
                "En az bir alan değiştirilmelidir: display_name, email veya new_password"
            )
        return self
