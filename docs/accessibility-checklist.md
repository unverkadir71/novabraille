# Erişilebilirlik Checklist — Nova Braille

> Kaynak: Plan v9 Bölüm 1.12. Hedef: WCAG 2.2 Level AA.
> Birincil test kombinasyonu: Windows 11 + NVDA + Microsoft Edge, klavye + Edge.

## 1. Semantic HTML ve Yapı

- [ ] Sayfada yalnızca bir `<h1>` var, başlık sayfanın amacını açıklıyor
- [ ] Heading hierarchy hatasız: h1 → h2 → h3, seviye atlanmıyor
- [ ] Landmark'lar tanımlı: `<main>`, `<nav>`, `<header>`/banner, `<footer>`/contentinfo
- [ ] `<nav>` elementi `aria-label` ile adlandırılmış (birden fazla nav varsa)
- [ ] Tablolar `<table>` ile işaretlenmiş, `<th>` ve `scope` kullanılmış (masaüstü tarayıcıda erişim için önemli)
- [ ] Liste öğeleri `<ul>/<ol>/<li>` ile işaretlenmiş

## 2. Skip-Link ve Navigasyon

- [ ] Sayfanın ilk odaklanabilir öğesi "Ana içeriğe atla" bağlantısı
- [ ] Skip-link görünür focus alıyor (gizli değil)
- [ ] Skip-link hedefi `<main id="main-content">` veya eşdeğeri
- [ ] Dashboard sidebar `<nav>` elementi, `aria-label="Ana menü"` ile
- [ ] Aktif sayfa `aria-current="page"` ile işaretli
- [ ] Mobil menü açık/kapalı durumu `aria-expanded` ile bildiriliyor

## 3. Klavye Erişimi

- [ ] Tüm etkileşimli öğelere Tab ile ulaşılabiliyor
- [ ] Shift+Tab ile geriye doğru gezilebiliyor
- [ ] Focus sırası mantıklı (DOM sırasıyla uyumlu)
- [ ] Focus tuzağı (keyboard trap) YOK — her yerden Tab ile çıkılabiliyor
- [ ] Enter/Space ile butonlar, linkler aktifleşiyor
- [ ] Escape ile modal/dialog kapanıyor
- [ ] Ok tuşları ile combo box, tab list, radio group geziliyor
- [ ] Özel klavye kısayolları varsa: NVDA komutlarıyla çakışmıyor
- [ ] Çakışan kısayollar varsa: kullanıcı tarafından değiştirilebiliyor veya kaldırılmış

## 4. Görünür Focus

- [ ] Tüm odaklanabilir öğelerde focus göstergesi görünür
- [ ] Focus göstergesi yeterli kontrasta sahip (en az 3:1)
- [ ] Focus göstergesi içerik tarafından örtülmüyor (z-index sorunu yok)
- [ ] `:focus-visible` tercih edilmiş (fare tıklamasında focus halkası çıkmaz)
- [ ] Özel focus stili varsa, `outline: none` kullanılmamış; yerine görünür alternatif

## 5. Renk ve Kontrast

- [ ] Normal metin kontrastı en az 4.5:1
- [ ] Büyük metin (18px+/bold 14px+) kontrastı en az 3:1
- [ ] UI bileşenleri ve grafik öğeler kontrastı en az 3:1
- [ ] Bilgi sadece renkle iletilmiyor (örn. hata durumu renk + ikon + metin)
- [ ] Linkler sadece renkle değil, altı çizili veya başka bir şekilde ayırt ediliyor

## 6. Forced Colors (Yüksek Karşıtlık Modu)

- [ ] Windows High Contrast / forced-colors modunda tüm içerik okunabiliyor
- [ ] Butonlar, input'lar ve kontroller forced-colors'ta görünür
- [ ] SVG ikonlar `currentColor` kullanıyor
- [ ] `forced-colors: active` media query ile gerekli düzeltmeler yapılmış

## 7. Zoom ve Reflow

- [ ] %400 zoom (veya 1280px genişlikte 320 CSS px) seviyesinde yatay kaydırma YOK
- [ ] İçerik %200 zoom'da taşmıyor veya kırpılmıyor
- [ ] Metin boşluğu (letter-spacing, word-spacing, line-height) ayarları bozulmuyor
- [ ] Tarayıcı zoom'u ile tüm işlevler kullanılabiliyor

## 8. prefers-reduced-motion

- [ ] Animasyon ve geçişler `prefers-reduced-motion: reduce` ile duruyor
- [ ] Otomatik oynayan video/animasyon yok (varsa durdurma kontrollü)
- [ ] `scroll-behavior: smooth` reduced-motion'da kapatılıyor

## 9. Formlar ve Hata Yönetimi

- [ ] Tüm input'larda `<label>` (açık veya örtük) veya `aria-label` var
- [ ] Zorunlu alanlar görsel olarak ve programatik olarak işaretli (`aria-required`, `required`)
- [ ] Hata mesajları metinle açıklanıyor
- [ ] Hata mesajı ilgili input'a `aria-describedby` ile bağlı
- [ ] Form gönderimi sonrası hata odağı ilk hatalı alana taşınıyor
- [ ] Başarılı işlem sonrası durum mesajı `aria-live="polite"` ile duyuruluyor
- [ ] Parola alanlarında `autocomplete="new-password"` / `autocomplete="current-password"`
- [ ] Yapıştırma (paste) işlemi kapatılmamış
- [ ] Parola görünürlük toggle'ı erişilebilir ada sahip

## 10. ARIA Kullanımı

- [ ] ARIA sadece native HTML yetmediğinde kullanılmış
- [ ] `aria-label` veya `aria-labelledby`: görünür metni tekrar etmiyor, anlamlı
- [ ] `aria-live` bölgeleri: `polite` tercih edilmiş, `assertive` sadece kritik durumlarda
- [ ] `aria-live` içeriği özlü — uzun metinler okunmuyor
- [ ] Custom widget varsa: ARIA Authoring Practices'a uygun

## 11. Dokunmatik ve Mobil

- [ ] Tıklanabilir hedefler en az 24×24 CSS piksel (mümkünse daha büyük)
- [ ] Hedefler arası yeterli boşluk var (yanlışlıkla tıklama önleme)
- [ ] Yatay modda içerik okunabilir ve kullanılabilir
- [ ] Android TalkBack ile kritik akışlar test edildi (login, çeviri, profil)

## 12. Medya ve Alternatifler

- [ ] Tüm img'lerde anlamlı `alt` metni var (dekoratifse boş `alt=""`)
- [ ] SVG'lerde `<title>` ve gerekiyorsa `<desc>` var
- [ ] Video varsa altyazı ve transkript
- [ ] Ses varsa transkript

## 13. CAPTCHA ve Güvenlik

- [ ] CAPTCHA varsa erişilebilir alternatif mevcut (sesli CAPTCHA, e-posta doğrulama)
- [ ] CAPTCHA yoksa: rate limiting + token mekanizması kullanılıyor
- [ ] Timeout varsa kullanıcıya uzatma seçeneği sunuluyor
- [ ] Session expiry öncesi uyarı veriliyor

## 14. Dokümantasyon ve Yardım

- [ ] Yardım/destek bağlantısı tüm sayfalarda tutarlı konumda
- [ ] İletişim sayfasında e-posta alternatifi var (form tek seçenek değil)
- [ ] Erişilebilirlik bildirimi sayfası mevcut (Faz 3)

## 15. NVDA + Edge Test Script'i

Aşağıdaki adımlar her release'de manuel tekrarlanır:

1. **Sayfa yükleme:** NVDA açıkken sayfayı aç. Sayfa başlığı okunuyor mu? Landmark'lar duyuruluyor mu?
2. **H tuşu ile başlık gezintisi:** Tüm heading'lere H/Shift+H ile ulaşılıyor mu?
3. **D tuşu ile landmark gezintisi:** Tüm landmark'lar arasında geçiş yapılabiliyor mu?
4. **Tab ile form gezintisi:** Her input'a ulaşılıyor, label'ı okunuyor mu?
5. **Insert+F7 ile bağlantı listesi:** Tüm linkler anlamlı metne sahip mi? "Buraya tıklayın" yok mu?
6. **Form gönderimi:** Validasyon hatası çıkınca NVDA odağı ilk hataya taşıyor mu? Hata mesajı okunuyor mu?
7. **Çeviri sonucu:** Braille çıktısı ekrana geldiğinde NVDA duyurusu çalışıyor mu?
8. **Modal/dialog:** Açılınca odak modal içine taşınıyor mu? Escape ile kapanıyor mu?
9. **Sayfa yeniden yükleme:** Sayfa yenilendiğinde focus korunuyor mu (gerekli yerlerde)?
10. **Insert+F5 ile form alanı listesi:** Tüm form kontrolleri listede görünüyor mu?

## 16. Kontrol Edilecek Araçlar

- [ ] axe DevTools / Lighthouse otomatik tarama (0 critical, 0 serious)
- [ ] NVDA + Edge manuel test
- [ ] Sadece klavye testi (fare kapalı)
- [ ] Windows Büyüteç ile %400 test
- [ ] Windows High Contrast / forced-colors test
- [ ] Android TalkBack (kritik akışlar: login, çeviri, profil)