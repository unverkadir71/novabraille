// Nova Braille — Admin Placeholder (billing ertelendi)
//
// F4.15 (Abonelikler), F4.16 (Ödeme Ayarları), F4.17 (Gelir Raporları)
// Billing entegrasyonu mali müşavir görüşmesi sonrası (F1.4 ertelendi).
// Bu sayfalar şimdilik yapılandırılmış boş durum gösterir.

(function () {
  "use strict";

  async function initPlaceholder(options) {
    try {
      await window.NovaAdmin.initAdminShell();
    } catch (err) {
      return;
    }

    const container = document.getElementById("placeholder-content");
    if (!container) {
      return;
    }

    const box = document.createElement("div");
    box.className = "state-box";

    const h = document.createElement("h2");
    h.textContent = options.title;
    box.appendChild(h);

    const p = document.createElement("p");
    p.textContent = options.message;
    box.appendChild(p);

    const note = document.createElement("p");
    note.className = "field-hint";
    note.textContent = "Ödeme altyapısı entegrasyonu planlama aşamasındadır. Bu bölüm, faturalandırma sağlayıcısı seçildikten sonra etkinleştirilecektir.";
    box.appendChild(note);

    container.appendChild(box);
  }

  window.NovaAdminPlaceholder = { initPlaceholder };
})();
