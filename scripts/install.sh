#!/usr/bin/env bash
# Nova Braille — Self-Hosted Kurulum Script'i
#
# Tek komutla kurulum:
#   curl -fsSL https://get.novabraille.com | bash
#
# Docker gerektirir. İnteraktif olarak admin bilgilerini sorar.

set -euo pipefail

# Renkler
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}╔══════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║       Nova Braille — Kurulum             ║${NC}"
echo -e "${CYAN}║       Braille Çeviri Web Uygulaması      ║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════════╝${NC}"
echo ""

# ── Docker kontrolü ───────────────────────────────────────────

if ! command -v docker &>/dev/null; then
    echo -e "${RED}HATA: Docker bulunamadı.${NC}"
    echo "Nova Braille Docker ile çalışır. Lütfen önce Docker'ı kurun:"
    echo "  https://docs.docker.com/engine/install/"
    exit 1
fi

if ! docker info &>/dev/null; then
    echo -e "${RED}HATA: Docker çalışmıyor veya yetkiniz yok.${NC}"
    echo "Docker daemon'unun çalıştığından ve kullanıcınızın docker grubunda olduğundan emin olun."
    exit 1
fi

# ── Admin bilgileri ────────────────────────────────────────────

echo -e "${YELLOW}Yönetici hesabı oluşturuluyor...${NC}"
echo ""

while true; do
    read -r -p "Admin e-posta adresi: " ADMIN_EMAIL
    if [[ -n "$ADMIN_EMAIL" && "$ADMIN_EMAIL" == *@*.* ]]; then
        break
    fi
    echo -e "${RED}Geçerli bir e-posta adresi girin.${NC}"
done

while true; do
    read -r -s -p "Admin parolası (en az 8 karakter): " ADMIN_PASSWORD
    echo ""
    if [[ ${#ADMIN_PASSWORD} -ge 8 ]]; then
        read -r -s -p "Parolayı tekrar girin: " ADMIN_PASSWORD_CONFIRM
        echo ""
        if [[ "$ADMIN_PASSWORD" == "$ADMIN_PASSWORD_CONFIRM" ]]; then
            break
        fi
        echo -e "${RED}Parolalar eşleşmiyor.${NC}"
    else
        echo -e "${RED}Parola en az 8 karakter olmalıdır.${NC}"
    fi
done

echo ""

# ── Port seçimi ────────────────────────────────────────────────

echo -e "${YELLOW}Port yapılandırması...${NC}"
echo ""

while true; do
    read -r -p "Port (varsayılan: 9876): " PORT
    PORT="${PORT:-9876}"
    if [[ "$PORT" =~ ^[0-9]+$ ]] && [ "$PORT" -ge 1 ] && [ "$PORT" -le 65535 ]; then
        break
    fi
    echo -e "${RED}Geçerli bir port numarası girin (1-65535).${NC}"
done

echo ""

# ── SMTP (isteğe bağlı) ───────────────────────────────────────

read -r -p "SMTP yapılandırmak ister misiniz? (e/h, varsayılan: h): " WANT_SMTP
WANT_SMTP="${WANT_SMTP:-h}"

SMTP_ENV=""
if [[ "$WANT_SMTP" =~ ^[eE] ]]; then
    echo -e "${YELLOW}SMTP yapılandırması...${NC}"
    echo ""

    # SMTP sunucusu — boş geçilemez
    while true; do
        read -r -p "SMTP sunucusu (örn: smtp.gmail.com): " SMTP_HOST
        if [[ -n "$SMTP_HOST" ]]; then
            break
        fi
        echo -e "${RED}SMTP sunucusu zorunludur.${NC}"
    done

    # SMTP port — boş geçilemez, geçerli sayı olmalı
    while true; do
        read -r -p "SMTP port (varsayılan: 587): " SMTP_PORT
        SMTP_PORT="${SMTP_PORT:-587}"
        if [[ "$SMTP_PORT" =~ ^[0-9]+$ ]] && [ "$SMTP_PORT" -ge 1 ] && [ "$SMTP_PORT" -le 65535 ]; then
            break
        fi
        echo -e "${RED}Geçerli bir port numarası girin (1-65535).${NC}"
    done

    # SMTP kullanıcı adı — boş geçilemez
    while true; do
        read -r -p "SMTP kullanıcı adı: " SMTP_USER
        if [[ -n "$SMTP_USER" ]]; then
            break
        fi
        echo -e "${RED}SMTP kullanıcı adı zorunludur.${NC}"
    done

    # SMTP şifresi — boş geçilemez
    while true; do
        read -r -s -p "SMTP şifresi: " SMTP_PASS
        echo ""
        if [[ -n "$SMTP_PASS" ]]; then
            read -r -s -p "SMTP şifresi (tekrar): " SMTP_PASS_CONFIRM
            echo ""
            if [[ "$SMTP_PASS" == "$SMTP_PASS_CONFIRM" ]]; then
                break
            fi
            echo -e "${RED}Şifreler eşleşmiyor.${NC}"
        else
            echo -e "${RED}SMTP şifresi zorunludur.${NC}"
        fi
    done

    # Gönderen e-posta — boş geçilemez
    while true; do
        read -r -p "Gönderen e-posta (varsayılan: $ADMIN_EMAIL): " SMTP_FROM
        SMTP_FROM="${SMTP_FROM:-$ADMIN_EMAIL}"
        if [[ -n "$SMTP_FROM" && "$SMTP_FROM" == *@*.* ]]; then
            break
        fi
        echo -e "${RED}Geçerli bir e-posta adresi girin.${NC}"
    done

    SMTP_ENV="
      - SMTP_HOST=$SMTP_HOST
      - SMTP_PORT=$SMTP_PORT
      - SMTP_USER=$SMTP_USER
      - SMTP_PASSWORD=$SMTP_PASS
      - SMTP_FROM=$SMTP_FROM"
fi

# ── Image çekme ve başlatma ───────────────────────────────────

echo ""
echo -e "${GREEN}Nova Braille başlatılıyor...${NC}"

SECRET_KEY=$(openssl rand -hex 32 2>/dev/null || python3 -c "import secrets; print(secrets.token_hex(32))")

docker run -d \
    --name nova-braille \
    --restart unless-stopped \
    -p "$PORT:9876" \
    -e APP_MODE=self_hosted \
    -e DATABASE_URL=sqlite+aiosqlite:///data/nova-braille.db \
    -e SECRET_KEY="$SECRET_KEY" \
    -e NOVA_ADMIN_EMAIL="$ADMIN_EMAIL" \
    -e NOVA_ADMIN_PASSWORD="$ADMIN_PASSWORD" \
    -e PORT="$PORT" \
    $SMTP_ENV \
    -v nova-braille-data:/data \
    ghcr.io/kadirunver/novabraille:beta

echo ""
echo -e "${GREEN}╔══════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║       Nova Braille kuruldu!              ║${NC}"
echo -e "${GREEN}╠══════════════════════════════════════════╣${NC}"
echo -e "${GREEN}║                                          ║${NC}"
echo -e "${GREEN}║   Adres:  http://localhost:$PORT            ║${NC}"
echo -e "${GREEN}║   E-posta: $ADMIN_EMAIL${NC}"
echo -e "${GREEN}║                                          ║${NC}"
echo -e "${GREEN}║   ${YELLOW}İlk girişte admin panelinden${NC}           ${GREEN}║${NC}"
echo -e "${GREEN}║   ${YELLOW}SMTP ayarlarını yapılandırın.${NC}            ${GREEN}║${NC}"
echo -e "${GREEN}║                                          ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════╝${NC}"
echo ""
echo "Konteyner logları:  docker logs -f nova-braille"
echo "Durdurmak için:     docker stop nova-braille"
echo "Kaldırmak için:     docker rm -f nova-braille && docker volume rm nova-braille-data"
