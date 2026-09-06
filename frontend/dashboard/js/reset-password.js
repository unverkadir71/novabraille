// Nova Braille — Parola Sıfırlama Onayı
//
// F4.2 — URL'den ?token= alır.
// POST /api/v1/auth/reset-password

(function () {
  "use strict";

  const form = document.getElementById("reset-form");
  const tokenInput = document.getElementById("token");
  const passwordInput = document.getElementById("password");
  const statusEl = document.getElementById("reset-status");
  const submitBtn = document.getElementById("reset-submit");

  const params = new URLSearchParams(window.location.search);
  if (params.get("token")) {
    tokenInput.value = params.get("token");
  }

  form.addEventListener("submit", async function (event) {
    event.preventDefault();

    const token = tokenInput.value.trim();
    const password = passwordInput.value;

    if (!token || !password) {
      window.NovaUi.showStatus(statusEl, "Sıfırlama kodu ve parola zorunludur.", "error");
      return;
    }
    if (password.length < 8) {
      window.NovaUi.showStatus(statusEl, "Parola en az 8 karakter olmalıdır.", "error");
      passwordInput.focus();
      return;
    }

    submitBtn.disabled = true;
    submitBtn.textContent = "Sıfırlanıyor…";
    window.NovaUi.showStatus(statusEl, "", null);

    try {
      await window.NovaApi.apiPost(
        "/api/v1/auth/reset-password",
        { token: token, password: password },
        { csrf: false }
      );
      window.NovaUi.showStatus(
        statusEl,
        "Parolanız başarıyla sıfırlandı. Giriş sayfasına yönlendiriliyorsunuz…",
        "success"
      );
      setTimeout(function () {
        window.location.href = "login.html";
      }, 2000);
    } catch (err) {
      window.NovaUi.showStatus(
        statusEl,
        (err && err.message) || "Parola sıfırlama başarısız oldu.",
        "error"
      );
    } finally {
      submitBtn.disabled = false;
      submitBtn.textContent = "Parolayı Sıfırla";
    }
  });
})();
