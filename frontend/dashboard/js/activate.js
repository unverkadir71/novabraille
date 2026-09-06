// Nova Braille — Hesap Etkinleştirme
//
// F4.2 — URL'den ?token= alır, kullanıcı parola belirler.
// POST /api/v1/auth/activate

(function () {
  "use strict";

  const form = document.getElementById("activate-form");
  const tokenInput = document.getElementById("token");
  const displayNameInput = document.getElementById("display-name");
  const passwordInput = document.getElementById("password");
  const statusEl = document.getElementById("activate-status");
  const submitBtn = document.getElementById("activate-submit");

  // URL'den token'ı otomatik doldur
  const params = new URLSearchParams(window.location.search);
  if (params.get("token")) {
    tokenInput.value = params.get("token");
  }

  form.addEventListener("submit", async function (event) {
    event.preventDefault();

    const token = tokenInput.value.trim();
    const password = passwordInput.value;

    if (!token || !password) {
      window.NovaUi.showStatus(statusEl, "Aktivasyon kodu ve parola zorunludur.", "error");
      return;
    }
    if (password.length < 8) {
      window.NovaUi.showStatus(statusEl, "Parola en az 8 karakter olmalıdır.", "error");
      passwordInput.focus();
      return;
    }

    submitBtn.disabled = true;
    submitBtn.textContent = "Etkinleştiriliyor…";
    window.NovaUi.showStatus(statusEl, "", null);

    try {
      await window.NovaApi.apiPost(
        "/api/v1/auth/activate",
        {
          token: token,
          password: password,
          display_name: displayNameInput.value.trim() || null,
        },
        { csrf: false }
      );
      window.NovaUi.showStatus(
        statusEl,
        "Hesabınız başarıyla etkinleştirildi. Giriş sayfasına yönlendiriliyorsunuz…",
        "success"
      );
      setTimeout(function () {
        window.location.href = "login.html";
      }, 2000);
    } catch (err) {
      window.NovaUi.showStatus(
        statusEl,
        (err && err.message) || "Etkinleştirme başarısız oldu.",
        "error"
      );
    } finally {
      submitBtn.disabled = false;
      submitBtn.textContent = "Etkinleştir";
    }
  });
})();
