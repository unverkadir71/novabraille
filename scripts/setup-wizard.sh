#!/usr/bin/env bash
# Nova Braille — Terminal Onboarding Sihirbazı (F7.6)
#
# İlk kurulum sonrası Docker container içinde çalışır.
# SMTP ayarlarını yapılandırır veya atlamaya izin verir.
# Admin kurulumu zaten install.sh tarafından yapılmıştır.

set -euo pipefail

# API base — container içinde localhost
API="http://localhost:9876/api/v1"

# Renkler
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}╔══════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║       Nova Braille — İlk Kurulum         ║${NC}"
echo -e "${CYAN}║       Terminal Onboarding                ║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════════╝${NC}"
echo ""

# ── Admin girişi ──────────────────────────────────────────────

echo -e "${YELLOW}Admin girişi yapın.${NC}"
echo ""

# Login al
LOGIN_RESPONSE=$(curl -s -c /tmp/nova-cookies.txt -X POST "$API/auth/login" \
    -F "email=$NOVA_ADMIN_EMAIL" \
    -F "password=$NOVA_ADMIN_PASSWORD" 2>&1) || true

if echo "$LOGIN_RESPONSE" | grep -q '"message"'; then
    echo -e "${GREEN}Giriş başarılı.${NC}"
else
    echo -e "${RED}Giriş başarısız. Admin bilgilerinizi kontrol edin.${NC}"
    echo "Yanıt: $LOGIN_RESPONSE"
    exit 1
fi

echo ""

# CSRF token al
CSRF_TOKEN=$(grep 'nova_csrf' /tmp/nova-cookies.txt | awk '{print $NF}')

# ── SMTP yapılandırması ───────────────────────────────────────

echo -e "${YELLOW}SMTP yapılandırması${NC}"
echo ""
echo "SMTP, e-posta gönderimi için gereklidir. Aktivasyon e-postaları,"
echo "parola sıfırlama ve bildirimler SMTP üzerinden gönderilir."
echo ""

while true; do
    read -r -p "SMTP'yi şimdi yapılandırmak ister misiniz? (E/h): " WANT_SMTP
    WANT_SMTP="${WANT_SMTP:-e}"

    case "${WANT_SMTP,,}" in
        e|evet|y|yes) WANT_SMTP="yes"; break ;;
        h|hayir|n|no) WANT_SMTP="no"; break ;;
        *) echo -e "${RED}Lütfen E (evet) veya H (hayır) girin.${NC}" ;;
    esac
done

echo ""

if [[ "$WANT_SMTP" == "yes" ]]; then
    echo -e "${YELLOW}SMTP sunucu bilgilerini girin.${NC}"
    echo "Tüm alanlar zorunludur."
    echo ""

    while true; do
        read -r -p "SMTP sunucusu (örn: smtp.gmail.com): " SMTP_HOST
        [[ -n "$SMTP_HOST" ]] && break
        echo -e "${RED}SMTP sunucusu zorunludur.${NC}"
    done

    while true; do
        read -r -p "SMTP port (varsayılan: 587): " SMTP_PORT
        SMTP_PORT="${SMTP_PORT:-587}"
        [[ "$SMTP_PORT" =~ ^[0-9]+$ ]] && [ "$SMTP_PORT" -ge 1 ] && [ "$SMTP_PORT" -le 65535 ] && break
        echo -e "${RED}Geçerli bir port girin (1-65535).${NC}"
    done

    while true; do
        read -r -p "SMTP kullanıcı adı: " SMTP_USER
        [[ -n "$SMTP_USER" ]] && break
        echo -e "${RED}SMTP kullanıcı adı zorunludur.${NC}"
    done

    while true; do
        read -r -s -p "SMTP şifresi: " SMTP_PASS
        echo ""
        [[ -n "$SMTP_PASS" ]] || { echo -e "${RED}SMTP şifresi zorunludur.${NC}"; continue; }
        read -r -s -p "SMTP şifresi (tekrar): " SMTP_PASS_CONFIRM
        echo ""
        [[ "$SMTP_PASS" == "$SMTP_PASS_CONFIRM" ]] && break
        echo -e "${RED}Şifreler eşleşmiyor.${NC}"
    done

    while true; do
        read -r -p "Gönderen adı (varsayılan: Nova Braille): " SMTP_FROM_NAME
        SMTP_FROM_NAME="${SMTP_FROM_NAME:-Nova Braille}"
        [[ -n "$SMTP_FROM_NAME" ]] && break
    done

    while true; do
        read -r -p "Gönderen e-posta (varsayılan: $NOVA_ADMIN_EMAIL): " SMTP_FROM_EMAIL
        SMTP_FROM_EMAIL="${SMTP_FROM_EMAIL:-$NOVA_ADMIN_EMAIL}"
        [[ "$SMTP_FROM_EMAIL" == *@*.* ]] && break
        echo -e "${RED}Geçerli bir e-posta adresi girin.${NC}"
    done

    echo ""
    echo -e "${GREEN}SMTP ayarları kaydediliyor...${NC}"

    SMTP_RESPONSE=$(curl -s -b /tmp/nova-cookies.txt -X PUT "$API/admin/smtp" \
        -H "Content-Type: application/json" \
        -H "X-CSRF-Token: $CSRF_TOKEN" \
        -d "$(cat <<JSON
{
  "enabled": true,
  "host": "$SMTP_HOST",
  "port": $SMTP_PORT,
  "username": "$SMTP_USER",
  "password": "$SMTP_PASS",
  "from_name": "$SMTP_FROM_NAME",
  "from_email": "$SMTP_FROM_EMAIL",
  "use_tls": true
}
JSON
)" 2>&1)

    if echo "$SMTP_RESPONSE" | grep -q '"enabled"'; then
        echo -e "${GREEN}SMTP ayarları kaydedildi.${NC}"

        # Test e-postası
        echo "Test e-postası gönderiliyor..."
        TEST_RESPONSE=$(curl -s -b /tmp/nova-cookies.txt -X POST "$API/admin/smtp/test" \
            -H "X-CSRF-Token: $CSRF_TOKEN" 2>&1)

        if echo "$TEST_RESPONSE" | grep -q '"success":true'; then
            echo -e "${GREEN}Test e-postası başarıyla gönderildi.${NC}"
        else
            echo -e "${YELLOW}Test e-postası gönderilemedi. SMTP ayarlarını admin panelinden kontrol edin.${NC}"
        fi
    else
        echo -e "${RED}SMTP ayarları kaydedilemedi. Admin panelinden manuel yapılandırabilirsiniz.${NC}"
    fi
else
    echo -e "${YELLOW}SMTP yapılandırması atlandı.${NC}"
    echo "SMTP'yi daha sonra admin panelinden yapılandırabilirsiniz:"
    echo "  1. Tarayıcıdan giriş yapın"
    echo "  2. Admin Paneli → SMTP"
    echo "  3. Ayarları doldurup 'Etkin' toggle'ını açın"
fi

echo ""
echo -e "${GREEN}╔══════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║       Kurulum tamamlandı!                ║${NC}"
echo -e "${GREEN}╠══════════════════════════════════════════╣${NC}"
echo -e "${GREEN}║                                          ║${NC}"
echo -e "${GREEN}║   Nova Braille kullanıma hazır.           ║${NC}"
echo -e "${GREEN}║   Tarayıcıdan giriş yaparak               ║${NC}"
echo -e "${GREEN}║   Braille çeviriye başlayabilirsiniz.     ║${NC}"
echo -e "${GREEN}║                                          ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════╝${NC}"

# Temizlik
rm -f /tmp/nova-cookies.txt