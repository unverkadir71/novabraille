# Nova Braille — Monitoring ve Alerting
#
# Hosted ve self-hosted için sağlık kontrolü ve izleme yapılandırması.

## Healthcheck Endpoint

Uygulama `/health` endpoint'inde basit durum yanıtı döner:
```json
{"status": "ok"}
```

## Docker Healthcheck

Dockerfile'da tanımlı healthcheck her 30 saniyede bir `/health` endpoint'ini kontrol eder.
3 başarısız deneme sonrası konteyner unhealthy durumuna geçer.

## Önerilen İzleme Araçları

### Hosted
- **Uptime izleme:** UptimeRobot veya BetterStack — 1 dakika aralıklı `/health` ping
- **Log toplama:** structlog JSON çıktısı → Loki + Grafana
- **Metrik:** Prometheus + Grafana (opsiyonel, ileri faz)
- **Hata takibi:** Sentry (`SENTRY_DSN` env değişkeni)

### Self-Hosted
- **Temel izleme:** `docker stats` + `docker logs`
- **Disk kullanımı:** `df -h /var/lib/docker/volumes/nova-braille-data`
- **Opsiyonel:** Admin panelinde sistem durumu widget'ı (Faz 8)

## Log Formatı

structlog JSON çıktısı:
```json
{
  "event": "translation.completed",
  "level": "info",
  "user_id": "a1b2c3d4",
  "table_id": "tr-g2.ctb",
  "char_count": 1500,
  "timestamp": "2026-09-06T13:00:00+03:00"
}
```

## Kritik Log Olayları

| Olay | Seviye | Anlamı |
|---|---|---|
| `auth.login_locked` | warning | Hesap kilitlendi (rate limit) |
| `auth.login_failure` | warning | Başarısız giriş denemesi |
| `email.failed` | error | E-posta gönderim hatası |
| `account.closed` | info | Hesap kapatıldı |
| `admin.role_changed` | info | Rol değişikliği |
| `rate_limit.hit` | warning | Rate limit tetiklendi |

## Alerting Kuralları (Önerilen)

1. **`email.failed` > 3/5dk** → SMTP sorunu, acil müdahale
2. **`auth.login_locked` > 5/saat** → Brute force saldırısı olabilir
3. **Healthcheck başarısız > 2dk** → Uygulama down
4. **Disk kullanımı > 80%** → Yakında sorun çıkabilir (hosted)
