# AGENTS.md — Nova Braille Proje Kuralları

> OpenCode ve diğer yapay zeka araçları için proje rehberi. 150 satırı aşmaz. Alt dizinlere nested AGENTS.md eklenebilir; en yakın dosya önceliklidir.

## Geliştirme Ortamı

```bash
# Sanal ortam ve bağımlılıklar
cd /root/.openclaw/workspace/nova-braille
export PATH="$HOME/.local/bin:$PATH"
uv venv
uv pip install -e ".[dev]"

# Liblouis Python binding (sistemde kurulu Liblouis 3.38.0'dan)
uv pip install --python .venv/bin/python /tmp/liblouis-3.38.0/python

# Aktivasyon
source .venv/bin/activate
```

**Gereksinimler:** Python >= 3.13, Liblouis 3.38.0 (sistem), UV 0.12+

## Build ve Test Komutları

```bash
# Lint
uv run ruff check backend/src/ tests/

# Type check
uv run mypy backend/src/

# Test (tümü)
uv run pytest tests/ -v

# Test (dosya bazlı, hızlı)
uv run pytest tests/test_translation/ -v

# Test + coverage
uv run pytest tests/ --cov=backend/src --cov-report=term-missing
```

**Kural:** `pytest tests/ -v` başarılı olmadan iş teslim edilmez.

## Kod Stili ve Konvansiyonlar

- PEP 8, 100 karakter satır genişliği
- Ruff: E, F, I, N, UP, B, SIM kuralları aktif
- `ruff format` ile otomatik formatlama
- mypy strict mod — tüm fonksiyonlar tip annotation'lı olmalı
- İthalat sırası: stdlib → üçüncü taraf → proje içi (ruff I kuralı)
- `from __future__ import annotations` tüm modüllerde
- SQLAlchemy modelleri ile Pydantic şemaları ayrı dosyalarda
- Router'lar HTTP detayları dışında iş mantığı içermez; servis katmanına yönlendirir

## Proje Dizin Yapısı

```
nova-braille/
├── backend/src/          # FastAPI uygulaması
│   ├── main.py           # Giriş noktası
│   ├── config.py         # Pydantic Settings
│   ├── database.py       # SQLAlchemy async engine + session
│   ├── api/v1/           # Router'lar (/api/v1/*)
│   ├── models/           # SQLAlchemy ORM modelleri
│   ├── schemas/          # Pydantic request/response şemaları
│   ├── services/         # İş mantığı (servis katmanı)
│   ├── billing/          # Ödeme adapter'ları
│   ├── translation/      # Çeviri motoru (liblouis wrapper, dosya işleme)
│   └── email/            # E-posta şablonları ve gönderim
├── frontend/
│   ├── public/           # Public site (novabraille.com)
│   ├── dashboard/        # Dashboard (app.novabraille.com)
│   └── shared/           # Ortak CSS/JS (design tokens, encryption)
├── tests/                # pytest (backend/src ile aynı yapı)
├── alembic/              # Veritabanı migration'ları
├── scripts/              # Kurulum ve yardımcı script'ler
├── deploy/               # Docker Compose, yedekleme
└── docs/                 # ADR ve belgeler
```

## Test Talimatları

- `tests/conftest.py`: async test client, test DB fixture'ları
- pytest-asyncio auto modda — async test fonksiyonları doğrudan yazılır
- Mock: harici servisler (ödeme, SMTP) için `unittest.mock` veya pytest-mock
- Her yeni model/service için en az bir integration test yazılır
- Braille doğruluğu: golden corpus fixture'ları ile `tests/test_translation/` altında
- Coverage hedefi: service katmanında >= %80

## İzin Sınırları

- `backend/src/` ve `tests/` dizinlerinde okuma/yazma: **otomatik onay**
- `alembic/` migration oluşturma: **otomatik onay**
- `pyproject.toml` bağımlılık ekleme: **otomatik onay**
- `frontend/` dosyaları: **otomatik onay**
- `.env`, `.env.example`, `README.md`: **otomatik onay**
- `.gitignore`, `alembic.ini`: **otomatik onay**
- `scripts/`, `deploy/`, `docs/`: **otomatik onay**
- Proje dizini dışına yazma: **ONAY GEREKİR**
- Production secrets içeren dosyalar: **KESİNLİKLE YASAK**
- `~/.openclaw` dizinine yazma: **KESİNLİKLE YASAK**

## Güvenlik Kuralları

- `.env` ve secrets dosyaları `.gitignore`'da
- API anahtarları ve şifreler environment variable üzerinden, kod içinde plaintext YOK
- Loglarda PII (kişisel veri), parola, session ID, token YOK
- Kullanıcı girdileri her zaman validate edilir
- Liblouis tablo ID'leri allowlist ile kontrol edilir

## Commit ve PR Kuralları

- Başlık formatı: `<type>: <kısa açıklama>` (örn. `feat: add translation service`)
- Tipler: feat, fix, refactor, test, docs, chore, ci
- Her commit tek bir mantıksal değişiklik içerir
- PR açılmadan önce lint + type check + test başarılı olmalı
- Migration içeren PR'larda rollback yolu belirtilir