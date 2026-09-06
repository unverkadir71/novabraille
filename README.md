# Nova Braille

> **Braille translation web application (beta)** — Fully compatible with screen
> readers and keyboard navigation. Text-to-Braille conversion in 8 languages.
> Run it on your own server for free.

[![License: AGPL-3.0](https://img.shields.io/badge/License-AGPL--3.0--or--later-blue.svg)](LICENSE)
[![GitHub release](https://img.shields.io/github/v/release/unverkadir71/novabraille)](https://github.com/unverkadir71/novabraille/releases)
[![Docker Pulls](https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fghcr.haya14busa.dev%2Fv2%2Funverkadir71%2Fnovabraille&query=$.pull_count&label=Docker%20Pulls)](https://github.com/users/unverkadir71/packages/container/package/novabraille)

![Nova Braille translation interface](assets/screenshot.png)

---

## ✨ Features

- Text → Braille and Braille → text translation in 8 languages (Liblouis 3.38.0)
- Supported languages: Türkçe, English, Deutsch, Français, Español, العربية, Русский, Português
- File input: DOCX, PDF, HTML, TXT and 5 more formats (9 formats total)
- Output formats: BRF (embosser), BRL (BrailleNote), and Unicode TXT (display)
- Dynamic contraction categories for each language
- Saved translation profiles
- Client-side encrypted translation history (PBKDF2 + AES-256-GCM)
- WCAG 2.2 AA compliant — tested with NVDA and keyboard-only navigation
- Single-command Docker setup — multi-arch (amd64 + arm64)
- Argon2id password hashing, CSRF protection, rate limiting
- OWASP 2026-compliant security headers (CSP, HSTS, X-Frame-Options)
- Discourse-style web-based admin panel

---

## 🌐 Supported Languages

Nova Braille translates text to and from Braille in 8 priority languages:

| Code | Language | Braille Tables | Contraction Support |
|------|----------|---------------|-------------------|
| `tr` | Türkçe | tr-g1.ctb, tr-g2.tbl | ✅ 7 categories |
| `en` | English | en-ueb-g1.ctb, en-ueb-g2.ctb | ✅ |
| `de` | Deutsch | de-g1.ctb, de-g2.ctb | ✅ |
| `fr` | Français | fr-bfu-g1.ctb, fr-bfu-g2.ctb | ✅ |
| `es` | Español | es-g1.ctb, es-g2.ctb | ✅ |
| `ar` | العربية | ar-g1.ctb, ar-g2.ctb | ✅ |
| `ru` | Русский | ru-litbrl.ctb, ru-litbrl-detailed.ctb | ✅ |
| `pt` | Português | pt-g1.ctb, pt-g2.ctb | ✅ |

The application interface supports all 8 languages as well. You can switch the UI language from the header at any time.

---

## 🚀 Quick Start

```bash
# 1. Pull the image (beta tag recommended for stability)
docker pull ghcr.io/unverkadir71/novabraille:beta

# 2. Run
docker run -d --name nova-braille --restart unless-stopped \
  -p 9876:9876 \
  -e APP_MODE=self_hosted \
  -e SECRET_KEY=$(openssl rand -hex 32) \
  -e NOVA_ADMIN_EMAIL=admin@example.com \
  -e NOVA_ADMIN_PASSWORD=strong-password-here \
  -v nova-braille-data:/data \
  ghcr.io/unverkadir71/novabraille:beta

# 3. Open in browser: http://localhost:9876
```

> **Tags:** `:beta` tracks the latest beta release. `:latest` also points to
> the same image during beta. Use `:beta` for explicit version intent.

Don't have Docker? See the [installation guide](https://docs.docker.com/engine/install/).

---

## 📦 Installation Methods

### Single command (interactive wizard)

```bash
curl -fsSL https://raw.githubusercontent.com/unverkadir71/novabraille/main/scripts/install.sh | bash
```

### Docker Compose (advanced users)

```bash
curl -O https://raw.githubusercontent.com/unverkadir71/novabraille/main/deploy/docker-compose.self-hosted.yml
# Edit the .env file with your settings
docker compose -f docker-compose.self-hosted.yml up -d
```

### Updating

```bash
docker pull ghcr.io/unverkadir71/novabraille:beta
docker stop nova-braille && docker rm nova-braille
# Re-run the docker run command above
```

---

## ⚙️ Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `NOVA_ADMIN_EMAIL` | ✅ | — | Initial admin email address |
| `NOVA_ADMIN_PASSWORD` | ✅ | — | Initial admin password (min 8 characters) |
| `SECRET_KEY` | ✅ | — | Generate with `openssl rand -hex 32` |
| `APP_MODE` | ❌ | `self_hosted` | `self_hosted` or `hosted` |
| `DATABASE_URL` | ❌ | `sqlite+aiosqlite:///data/nova-braille.db` | Database connection string |
| `PORT` | ❌ | `9876` | Web interface port |
| `SMTP_HOST` | ❌ | empty | SMTP server hostname |
| `SMTP_PORT` | ❌ | `587` | SMTP server port |
| `SMTP_USER` | ❌ | empty | SMTP username |
| `SMTP_PASSWORD` | ❌ | empty | SMTP password |
| `SMTP_FROM` | ❌ | `noreply@novabraille.local` | Sender email address |
| `SELF_HOSTED_REGISTRATION` | ❌ | `closed` | Registration policy: `open` or `closed` |

### System Requirements

| Resource | Minimal | Recommended |
|---|---|---|
| RAM | 512 MB | 1 GB |
| Disk | 500 MB | 2 GB |
| Docker | 20.10+ | 24+ |

---

## 🛠️ Development

```bash
# Requirements: Python >= 3.13, Liblouis 3.38.0, UV

git clone https://github.com/unverkadir71/novabraille.git
cd novabraille

# Virtual environment and dependencies
uv venv
source .venv/bin/activate
uv pip install -e ".[dev]"

# Tests (397 tests)
uv run pytest tests/ -v

# Development server
uv run uvicorn backend.src.main:app --reload
```

See [CONTRIBUTING.md](./CONTRIBUTING.md) for detailed contribution guidelines, code standards, and accessibility requirements.

---

## 🔒 Security

For vulnerability disclosure, see [SECURITY.md](./SECURITY.md).

- Password hashing: Argon2id (OWASP 2026), 64MB / 3 iterations / 4 threads
- Sessions: HttpOnly + SameSite=Lax cookie, server-side, 8-hour expiry
- CSRF: Double Submit Cookie
- Security headers: CSP, X-Frame-Options, X-Content-Type-Options, Referrer-Policy
- Rate limiting: 5 failures / 5 min → 15 min lockout
- SQL injection: SQLAlchemy ORM (parameterized queries)
- File security: Size limits, format validation, temporary file cleanup

---

## 📄 License

AGPL-3.0-or-later. See [LICENSE](./LICENSE) for the full text.

Third-party licenses: [THIRD_PARTY_NOTICES.md](./THIRD_PARTY_NOTICES.md).

---

## ⚠️ Beta Notice

This is a **beta release** (v1.0.0-beta). The core Braille translation engine and
all features are functional, but there are known gaps:

- The UI language selector supports 8 languages, but page content is not yet
  fully translated per locale — dynamic i18n is planned for v1.1.0.
- Braille output accuracy for Arabic, Russian, and Portuguese has not been
  validated by native speakers.
- Feedback and bug reports are welcome via GitHub Issues.

## 📚 Documentation

- Contributing: [CONTRIBUTING.md](./CONTRIBUTING.md)
- Security policy: [SECURITY.md](./SECURITY.md)
- Release notes: [CHANGELOG.md](./CHANGELOG.md)
- Trademark policy: [TRADEMARKS.md](./TRADEMARKS.md)
- Code of conduct: [CODE_OF_CONDUCT.md](./CODE_OF_CONDUCT.md)
