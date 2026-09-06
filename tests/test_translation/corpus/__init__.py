# Turkish reference corpus — Braille çeviri doğrulama
#
# Her giriş: (text, braille_contracted, braille_uncontracted)
# Plan v9 referansı: Bölüm 1.10.9 — Doğrulama Testleri
# Memory.md: tr-g2.tbl kısaltmalı, tr-g1.ctb kısaltmasız

# Format: list of (source_text, table_id, expected_output_or_empty)
TURKISH_CORPUS = [
    # Temel kelimeler
    ("Merhaba", "tr-g2.tbl", ""),  # Kısaltmalı çıktı
    ("dünya", "tr-g2.tbl", ""),
    ("Türkçe", "tr-g2.tbl", ""),

    # Sayılar
    ("123", "tr-g2.tbl", ""),
    ("2024 yılı", "tr-g2.tbl", ""),

    # Büyük harf
    ("ANKARA", "tr-g1.ctb", ""),
    ("İstanbul", "tr-g1.ctb", ""),

    # Özel karakterler
    ("Merhaba dünya!", "tr-g1.ctb", ""),
    ("Fiyat: 15,50 TL", "tr-g1.ctb", ""),

    # Cümleler
    ("Bu bir test cümlesidir.", "tr-g2.tbl", ""),
    ("Kadir için Braille çeviri testi.", "tr-g2.tbl", ""),

    # Kısaltma kontrolleri (G2)
    ("ve", "tr-g2.tbl", ""),  # Tek harf kısaltması
    ("için", "tr-g2.tbl", ""),  # İki harf kısaltması
]

# Her dil için minimum round-trip test verileri — 8 öncelikli dil
ROUND_TRIP_CORPUS = [
    # (text, table_id, supports_round_trip)
    ("Merhaba dünya", "tr-g1.ctb", True),
    ("Hello world", "en-ueb-g1.ctb", True),
    ("Guten Tag", "de-g1.ctb", True),
    ("Bonjour le monde", "fr-bfu-g2.ctb", True),
    ("Hola mundo", "es-g1.ctb", True),
    ("مرحبا بالعالم", "ar-ar-g1.utb", True),
    ("Привет мир", "ru-ru-g1.ctb", True),
    ("Olá mundo", "pt-pt-g1.utb", True),
]
