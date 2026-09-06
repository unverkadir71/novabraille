# Nova Braille — Third-Party License Notices

> Last updated: 2026-09-06

Nova Braille uses the following open source libraries.
Each library's full license text is available under `/usr/share/doc/` in the Docker image.

## Backend (Python)

| Library | Version | License |
|---|---|---|
| FastAPI | 0.141+ | MIT |
| Uvicorn | 0.32+ | BSD-3-Clause |
| SQLAlchemy | 2.0+ | MIT |
| Alembic | 1.14+ | MIT |
| asyncpg | 0.30+ | Apache-2.0 |
| Pydantic / pydantic-settings | 2+ | MIT |
| pwdlib (Argon2) | 0.2+ | MIT |
| argon2-cffi | 25+ | MIT |
| PyMuPDF | 1.28+ | AGPL-3.0 |
| openpyxl | 3.1+ | MIT |
| python-docx | 1.1+ | MIT |
| lxml | 6.0+ | BSD-3-Clause |
| Dramatiq | 2.2+ | LGPL-3.0-or-later |
| structlog | 26+ | MIT / Apache-2.0 |
| orjson | 3.10+ | MIT / Apache-2.0 |
| httpx | 0.28+ | BSD-3-Clause |
| tenacity | 9+ | Apache-2.0 |
| Jinja2 | 3.1+ | BSD-3-Clause |
| aiosmtplib | 3+ | MIT |
| python-multipart | 0.0.18+ | Apache-2.0 |
| cryptography | 50+ | Apache-2.0 / BSD-3-Clause |

## System Dependencies

| Tool | Version | License |
|---|---|---|
| Liblouis | 3.38.0 | LGPL-2.1-or-later |
| Pandoc | 3.10+ | GPL-2.0-or-later |
| Tesseract OCR | 5+ | Apache-2.0 |
| LibreOffice | 24+ | MPL-2.0 |

## Development Dependencies

| Library | License |
|---|---|
| pytest | MIT |
| pytest-asyncio | Apache-2.0 |
| pytest-cov | MIT |
| ruff | MIT |
| mypy | MIT |

## Notice

We thank the copyright holders of the libraries listed above.
This list is manually maintained and may be incomplete.
For the complete and up-to-date list, see the `uv.lock` file and the license
files under `/usr/local/lib/python3.13/site-packages/` in the Docker image.
