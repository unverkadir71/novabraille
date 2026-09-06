# Changelog

All notable changes to Nova Braille are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Planned for v1.1.0

- Full i18n: dynamic page content translation for all 8 UI languages
- CI/CD pipeline (GitHub Actions: lint, test, build, release)
- Additional round-trip tests for Arabic and Russian Braille tables

## [v1.0.0-beta] — 2026-09-06

> **Beta release.** Core features are functional and stable. Known limitations:
> - 8-language UI selector is active, but page content is not yet dynamically translated per locale (i18n coming in v1.1.0)
> - Braille output quality for Arabic, Russian, and Portuguese has not been fully validated by native speakers

### Added

- Initial beta release — self-hosted Braille translation web application
- Text → Braille and Braille → text translation in 8 languages (Liblouis 3.38.0)
- 9 input file formats: TXT, DOCX, DOC, RTF, ODT, HTML, PDF (digital + OCR), XLSX, DAISY/NIMAS
- 3 output formats: Unicode TXT (display), BRF (embosser), BRL (BrailleNote)
- Dynamic contraction system (checkbox categories for 8 languages)
- User-specific translation profiles
- Client-side encrypted translation history (PBKDF2 + AES-256-GCM)
- Argon2id password hashing (OWASP 2026 compliant)
- CSRF Double Submit Cookie protection
- Rate limiting (login brute-force protection)
- RBAC — hosted (4 roles) and self-hosted (2 roles)
- Discourse-style web-based admin panel
- SMTP admin panel management
- Public site (13 pages) + Dashboard (20 pages)
- WCAG 2.2 AA accessibility (NVDA + keyboard tested)
- Theme and language preferences (cookie-based)
- Dark mode support
- Docker multi-arch (amd64 + arm64), non-root user
- Single-command installation script (`curl | bash`)
- Docker Compose (self-hosted + hosted)
- GDPR-compliant data export and account deletion
- 397 pytest (unit + integration + API)
- axe-core accessibility scan across 39 pages (0 critical / 0 serious)
- OWASP 2026-compliant security headers (CSP, HSTS)

### License

AGPL-3.0-or-later

[Unreleased]: https://github.com/unverkadir71/novabraille/compare/v1.0.0-beta...main
[v1.0.0-beta]: https://github.com/unverkadir71/novabraille/releases/tag/v1.0.0-beta
