// Nova Braille — Parola Sıfırlama Talebi
//
// F4.2 — POST /api/v1/auth/send-password-reset
// Hesap varlığını ifşa etmeyen jenerik yanıt gösterir.

(function () {
  "use strict";

  const form = document.getElementById("forgot-form");
  const emailInput = document.getElementById("email");
  const statusEl = document.getElementById("forgot-status");
  const submitBtn = document.getElementById("forgot-submit");

  form.addEventListener("submit", async function (event) {
    event.preventDefault();

    const email = emailInput.value.trim();
    if (!email) {
      window.NovaUi.showStatus(statusEl, "E-posta adresi zorunludur.", "error");
      emailInput.focus();
      return;
    }

    submitBtn.disabled = true;
    submitBtn.textContent = "Gönderiliyor…";
    window.NovaUi.showStatus(statusEl, "", null);

    try {
      await window.NovaApi.apiPost(
        "/api/v1/auth/send-password-reset",
        { email: email },
        { csrf: false }
      );
      // Hesap varlığını ifşa etmeyen jenerik mesaj
      window.NovaUi.showStatus(
        statusEl,
        "Eğer bu e-posta ile kayıtlı bir hesabınız varsa, parola sıfırlama bağlantısı gönderildi. Lütfen gelen kutunuzu kontrol edin.",
        "success"
      );
    } catch (err) {
      // Jenerik mesaj — hata detayını ifşa etme
      window.NovaUi.showStatus(
        statusEl,
        "İstek işlenirken bir sorun oluştu. Lütfen daha sonra tekrar deneyin.",
        "error"
      );
    } finally {
      submitBtn.disabled = false;
      submitBtn.textContent = "Bağlantı Gönder";
    }
  });
})();
