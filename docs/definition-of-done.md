# Definition of Done — Nova Braille

> Kaynak: Plan v9 Bölüm 1.22. Her özellik (feature) ancak aşağıdaki tüm maddeler sağlandığında tamamlanmış sayılır.

## 1. Gereksinim ve Kabul Ölçütü

- [ ] Özelliğin ne yaptığı ve neden gerekli olduğu yazılı
- [ ] Kabul ölçütleri (acceptance criteria) net ve test edilebilir
- [ ] Kapsam dışı konular belirtilmiş
- [ ] İlgili ADR varsa referans verilmiş

## 2. Kod ve Testler

- [ ] Unit testler yazıldı ve geçiyor
- [ ] Integration testler yazıldı ve geçiyor
- [ ] Service katmanı coverage ≥ %80
- [ ] Kod Ruff lint ve format kurallarına uygun
- [ ] Mypy strict mod hatasız
- [ ] SQLAlchemy model(ler)i varsa Pydantic schema'sı ayrı dosyada
- [ ] Router sadece HTTP routing yapıyor; iş mantığı service katmanında
- [ ] `from __future__ import annotations` tüm yeni modüllerde
- [ ] İthalat sırası: stdlib → üçüncü taraf → proje içi

## 3. Yetkilendirme ve Hata Durumları

- [ ] Kimlik doğrulaması gereken endpoint'lerde 401 test edildi
- [ ] Yetki kontrolü gereken endpoint'lerde 403 test edildi
- [ ] Geçersiz giriş durumunda 422 ve alan bazlı hatalar test edildi
- [ ] Rate limit aşımında 429 test edildi
- [ ] Bağımlı servis hatasında uygun hata kodu (503)
- [ ] İstek boyutu sınırı ve timeout testi yapıldı
- [ ] Concurrent istek davranışı kontrol edildi (race condition, idempotency)
- [ ] Hata yanıtlarında iç exception detayı SIZMIYOR

## 4. NVDA ve Klavye Etkisi

- [ ] Semantic HTML öğeleri kullanıldı (heading, nav, main, button vs)
- [ ] Heading hierarchy doğru (h1 → h2 → h3, atlama yok)
- [ ] Landmark'lar tanımlı (main, nav, banner, contentinfo)
- [ ] Skip-link mevcut ve çalışıyor
- [ ] Tüm etkileşimli öğelere klavye ile erişilebiliyor (Tab/Shift+Tab)
- [ ] Focus sırası mantıklı ve görünür focus var
- [ ] aria-current="page" aktif sayfada
- [ ] aria-live bölgeleri durum mesajları için kullanıldı (abartılmadan)
- [ ] Form hataları metinle açıklanıyor ve ilgili alana bağlanıyor (aria-describedby)
- [ ] Yeni içerik eklenince focus yönetimi test edildi (kullanıcıyı zorla taşıma YOK)
- [ ] ARIA sadece zorunlu olduğunda kullanıldı; native HTML öncelikli
- [ ] Parola alanlarında autocomplete uygun

## 5. UI Metinleri

- [ ] Tüm görünür metinler Türkçe kaynak dosyasında (varsayılan dil)
- [ ] İngilizce çeviriler İngilizce kaynak dosyasında
- [ ] Sert kodlanmış (hardcoded) metin YOK
- [ ] Tarih/saat formatları locale'e uygun
- [ ] Hata mesajları kullanıcıya anlamlı ve Türkçe

## 6. Loglama

- [ ] Loglarda PII (e-posta, isim vb) YOK
- [ ] Loglarda parola, token, session ID YOK
- [ ] Loglarda çeviri metni veya Braille sonucu YOK
- [ ] Loglarda ödeme/kart verisi YOK
- [ ] Correlation ID her istekte mevcut
- [ ] structlog ile JSON formatlı log

## 7. Dokümantasyon

- [ ] API endpoint'i varsa docstring yazıldı
- [ ] Karmaşık iş mantığı varsa kod içi yorum
- [ ] README veya ilgili .md dosyası güncellendi
- [ ] .env.example'a yeni değişken eklendiyse belgelendi

## 8. Migration

- [ ] Migration dosyası oluşturuldu (alembic revision --autogenerate)
- [ ] `upgrade` ve `downgrade` test edildi
- [ ] Rollback senaryosu değerlendirildi (veri kaybı riski var mı?)
- [ ] SQLite ve PostgreSQL uyumluluğu kontrol edildi (batch mode)

## 9. CI

- [ ] `uv run ruff check` temiz
- [ ] `uv run ruff format --check` temiz
- [ ] `uv run mypy backend/src/` temiz
- [ ] `uv run pytest tests/ -v` tüm testler yeşil

## 10. İnsan İncelemesi

- [ ] Kod en az bir kez gözden geçirildi (Kadir veya reviewer)
- [ ] Manuel test adımları belgelendi
- [ ] Erişilebilirlik manuel kontrolü yapıldı (NVDA + klavye)
- [ ] Mobil/tablet görünümü kontrol edildi (responsive)

---

## Her Release İçin Ek Kontroller

- [ ] Tüm Faz 6 erişilebilirlik testleri tekrarlandı
- [ ] Braille golden corpus regression testi geçti
- [ ] Dependency vulnerability taraması temiz
- [ ] Migration rollback testi yapıldı
- [ ] CHANGELOG güncellendi