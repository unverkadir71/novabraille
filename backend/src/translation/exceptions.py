# Translation engine exceptions
#
# Custom exception hierarchy for the Liblouis wrapper.
# Plan v9 referansı: Faz 2.1 — Çeviri Çekirdeği

from __future__ import annotations


class TranslationError(Exception):
    """Tüm çeviri hatalarının taban sınıfı."""


class TableNotFoundError(TranslationError):
    """Belirtilen Braille tablosu bulunamadı.

    Attributes:
        table_id: Bulunamayan tablo kimliği
    """

    def __init__(self, table_id: str) -> None:
        self.table_id = table_id
        super().__init__(f"Braille table not found: {table_id!r}")


class TableCompileError(TranslationError):
    """Braille tablosu derlenemedi (syntax hatası veya bağımlılık sorunu).

    Attributes:
        table_id: Derlenemeyen tablo kimliği
        liblouis_message: Liblouis'ten gelen orijinal hata mesajı
    """

    def __init__(self, table_id: str, liblouis_message: str) -> None:
        self.table_id = table_id
        self.liblouis_message = liblouis_message
        super().__init__(
            f"Braille table compile error for {table_id!r}: {liblouis_message}"
        )


class EmptyInputError(TranslationError):
    """Çeviri girdisi boş veya yalnızca boşluk karakterlerinden oluşuyor."""

    def __init__(self) -> None:
        super().__init__("Translation input is empty")


class TranslationFailedError(TranslationError):
    """Liblouis çevirisi başarısız oldu (beklenmeyen iç hata).

    Attributes:
        direction: Çeviri yönü ('text_to_braille' | 'braille_to_text')
        table_id: Kullanılan tablo
        original_error: Orijinal istisna
    """

    def __init__(
        self,
        direction: str,
        table_id: str,
        original_error: Exception,
    ) -> None:
        self.direction = direction
        self.table_id = table_id
        self.original_error = original_error
        super().__init__(
            f"Translation failed ({direction}) with table {table_id!r}: {original_error}"
        )