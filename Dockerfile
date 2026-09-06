# Nova Braille — Production Dockerfile
#
# Multi-stage build, non-root user, python:3.13-slim base.
# Supports AMD64 and ARM64 (multi-arch).
#
# Build: docker build -t novabraille:latest .
# Run:   docker run -e NOVA_ADMIN_EMAIL=... -e NOVA_ADMIN_PASSWORD=... ...

# ── Stage 1: Dependencies ─────────────────────────────────────
FROM python:3.13-slim AS builder

RUN apt-get update && apt-get install -y --no-install-recommends \
    liblouis-dev \
    pandoc \
    tesseract-ocr \
    tesseract-ocr-tur \
    tesseract-ocr-eng \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY pyproject.toml .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -e ".[dev,test]" 2>/dev/null || \
    pip install --no-cache-dir \
    "fastapi>=0.115,<1" "uvicorn[standard]>=0.32" \
    "sqlalchemy[asyncio]>=2.0,<3" "asyncpg>=0.30" "alembic>=1.14" \
    "pydantic-settings>=2.7" "pydantic[email]>=2" \
    "pwdlib[argon2]>=0.2" "python-multipart>=0.0.18" \
    "pymupdf>=1.28" "openpyxl>=3.1" "python-docx>=1.1" "lxml>=6.0" \
    "dramatiq[redis]>=2.2" "structlog>=26.0" "orjson>=3.10" \
    "httpx>=0.28" "tenacity>=9" "jinja2>=3.1" "aiosmtplib>=3" \
    "cryptography>=50"

# ── Stage 2: Runtime ──────────────────────────────────────────
FROM python:3.13-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    liblouis-dev \
    pandoc \
    tesseract-ocr \
    tesseract-ocr-tur \
    tesseract-ocr-eng \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd --create-home --shell /bin/bash nova && \
    mkdir -p /app /data && chown -R nova:nova /app /data

# Copy Python packages from builder
COPY --from=builder /usr/local/lib/python3.13/site-packages /usr/local/lib/python3.13/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application
COPY --chown=nova:nova . /app

WORKDIR /app

# Environment
ENV PYTHONPATH=/app/backend \
    PYTHONUNBUFFERED=1 \
    APP_MODE=self_hosted \
    DATABASE_URL=sqlite+aiosqlite:///data/nova-braille.db \
    NOVA_ADMIN_EMAIL="" \
    NOVA_ADMIN_PASSWORD=""

USER nova

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:9876/health || exit 1

# Run database migrations and start server
CMD sh -c 'PYTHONPATH=/app/backend python -m alembic -c /app/alembic.ini upgrade head && \
    uvicorn backend.src.main:app --host 0.0.0.0 --port 9876'

EXPOSE 9876
