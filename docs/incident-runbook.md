# Nova Braille — Incident Runbook
#
# Canlıya alma sonrası olası sorunlar ve müdahale adımları.
# Hosted ve self-hosted için ortak/ayrı bölümler.

## Hosted — Altyapı

### PostgreSQL bağlantı hatası
1. `docker compose -f deploy/docker-compose.hosted.yml ps` — db konteyneri up mı?
2. `docker compose logs db | tail -20` — log kontrolü
3. Disk dolu mu? `df -h /var/lib/docker/volumes/`
4. Çözüm: `docker compose restart db` veya volume temizliği

### Redis bağlantı hatası
1. `docker compose logs redis | tail -10`
2. `docker compose restart redis`

### Worker e-posta göndermiyor
1. `docker compose logs worker | tail -20`
2. SMTP ayarları doğru mu? Admin panelinden kontrol et
3. `docker compose restart worker`

## Self-Hosted — Altyapı

### Uygulama başlamıyor
1. `docker logs nova-braille | tail -50`
2. `docker exec nova-braille ls /data/` — data dizini var mı?
3. Port çakışması: `netstat -tlnp | grep PORT`
4. Disk dolu mu? `df -h`

### Veritabanı bozulması (SQLite)
1. `docker stop nova-braille`
2. `docker run --rm -v nova-braille-data:/data alpine cp /data/nova-braille.db /data/nova-braille.db.bak`
3. `docker start nova-braille`
4. Hala çalışmıyorsa: `sqlite3 /var/lib/docker/volumes/nova-braille-data/_data/nova-braille.db "PRAGMA integrity_check;"`

## Her İki Mod — Ortak

### 502/503 hatası (uygulama yanıt vermiyor)
1. `curl -f http://localhost:9876/health`
2. CPU/memory: `docker stats`
3. `docker logs --tail 100 <konteyner> | grep -i error`
4. Restart: `docker compose restart app` veya `docker restart nova-braille`

### Rate limiting sorunu
- Kullanıcı kilitlendiyse: Admin paneli → Kullanıcılar → durumu aktif yap
- Rate limit süresi: 15 dakika (config'te değiştirilemez)

### E-posta gönderilmiyor
- Admin paneli → SMTP → "Etkin" toggle'ı açık mı?
- "Test E-postası Gönder" butonu ile test et
- Hosted: SMTP zorunludur, devre dışı bırakılamaz

### Yedekleme (Hosted)
```bash
# BorgBackup
borg create --stats ::{now:%Y-%m-%d_%H:%M} /var/lib/docker/volumes/pgdata

# Restic (off-site)
restic -r s3:s3.amazonaws.com/bucket-name backup /var/lib/docker/volumes/
```

### Rollback
1. `docker compose down`
2. `git checkout <önceki-tag>`
3. `docker compose build app worker`
4. `docker compose up -d`
5. Migration rollback (gerekirse): `docker compose run --rm app alembic downgrade -1`

### Migration hatası
1. `docker compose run --rm app alembic current` — mevcut revision
2. `docker compose run --rm app alembic history` — revision zinciri
3. Manuel düzeltme: `docker compose run --rm app alembic stamp <revision>`

## Acil Durum İletişimi

### Hosted
- Sistem durumu sayfası: https://status.novabraille.com
- Teknik destek: destek@novabraille.com
- Acil: Kadir Ünver

### Self-Hosted
- GitHub Issues: https://github.com/novabraille/novabraille/issues
- Topluluk: https://github.com/novabraille/novabraille/discussions

---

*Son güncelleme: 2026-09-06*
