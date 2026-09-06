// Nova Braille — Erişilebilir Çerez Bildirimi
//
// Nova Braille yalnızca zorunlu çerezler (oturum, CSRF koruması) kullanır.
// İzleme, reklam veya üçüncü taraf çerezi YOKTUR.
// Bu banner yalnızca bilgilendirme amaçlıdır; kullanıcı onayı gerektirmez
// çünkü zorunlu çerezler için onay alınması KVKK/GDPR kapsamında gerekmez.
//
// Erişilebilirlik:
// - role="dialog" ile ekran okuyucuya bildirilir
// - Odak otomatik olarak banner'a taşınır
// - Escape tuşu ile kapatılabilir
// - Tercih localStorage'da saklanır

(function () {
  "use strict";

  const STORAGE_KEY = "nova_braille_cookie_notice";

  function isDismissed() {
    try {
      return localStorage.getItem(STORAGE_KEY) === "dismissed";
    } catch (e) {
      return false;
    }
  }

  function dismiss() {
    try {
      localStorage.setItem(STORAGE_KEY, "dismissed");
    } catch (e) {
      /* localStorage erişilemezse sessizce geç */
    }
    const banner = document.getElementById("cookie-notice");
    if (banner) {
      banner.remove();
    }
  }

  function createBanner() {
    if (isDismissed()) {
      return;
    }

    const banner = document.createElement("section");
    banner.id = "cookie-notice";
    banner.setAttribute("role", "dialog");
    banner.setAttribute("aria-label", "Çerez bildirimi");
    banner.setAttribute("aria-describedby", "cookie-notice-text");

    banner.innerHTML =
      '<div class="cookie-notice-content">' +
      '<p id="cookie-notice-text">Nova Braille yalnızca oturum yönetimi için zorunlu çerezler kullanır. İzleme, reklam veya üçüncü taraf çerezi kullanılmaz. Detaylı bilgi için <a href="privacy.html">Gizlilik Politikası</a> sayfamızı inceleyebilirsiniz.</p>' +
      '<button type="button" id="cookie-notice-dismiss" class="btn btn-primary">Anladım</button>' +
      "</div>";

    document.body.appendChild(banner);

    const dismissBtn = document.getElementById("cookie-notice-dismiss");
    dismissBtn.addEventListener("click", dismiss);

    // Escape tuşu ile kapat
    dismissBtn.addEventListener("keydown", function (e) {
      if (e.key === "Escape") {
        dismiss();
      }
    });

    // Odağı butona taşı (yalnızca ilk yüklemede)
    dismissBtn.focus();
  }

  // DOM hazır olduğunda banner'ı oluştur
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", createBanner);
  } else {
    createBanner();
  }
})();
