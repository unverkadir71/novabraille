// Nova Braille — Login
//
// F4.2 — Giriş sayfası.
// POST /api/v1/auth/login (Form-encoded: email, password).
// Başarılı girişte index.html'e yönlendirir.
// "expired" query parametresi varsa oturum sona erme bildirimi gösterir.

(function () {
  "use strict";

  const form = document.getElementById("login-form");
  const emailInput = document.getElementById("email");
  const passwordInput = document.getElementById("password");
  const statusEl = document.getElementById("login-status");
  const submitBtn = document.getElementById("login-submit");

  // Oturum sona erme bildirimi
  const params = new URLSearchParams(window.location.search);
  if (params.get("expired") === "1") {
    window.NovaUi.showStatus(
      statusEl,
      "Oturumunuz sona erdi. Lütfen yeniden giriş yapın.",
      "info"
    );
  }

  // Zaten giriş yapılmışsa dashboard'a yönlendir
  async function redirectIfLoggedIn() {
    try {
      const user = await window.NovaApi.apiGet("/api/v1/auth/me");
      if (user && user.status === "active") {
        window.location.href = "index.html";
      }
    } catch (err) {
      // Giriş yapılmamış — normal akış
    }
  }
  redirectIfLoggedIn();

  form.addEventListener("submit", async function (event) {
    event.preventDefault();

    const email = emailInput.value.trim();
    const password = passwordInput.value;

    if (!email || !password) {
      window.NovaUi.showStatus(statusEl, "E-posta ve parola zorunludur.", "error");
      if (!email) emailInput.focus();
      else passwordInput.focus();
      return;
    }

    submitBtn.disabled = true;
    submitBtn.textContent = "Giriş yapılıyor…";
    window.NovaUi.showStatus(statusEl, "", null);

    try {
      await window.NovaApi.apiPostForm("/api/v1/auth/login", {
        email: email,
        password: password,
      });
      window.location.href = "index.html";
    } catch (err) {
      if (err && err.status === 429) {
        window.NovaUi.showStatus(
          statusEl,
          "Çok fazla başarısız deneme. 15 dakika sonra tekrar deneyin.",
          "error"
        );
      } else if (err && err.status === 401) {
        window.NovaUi.showStatus(statusEl, "Geçersiz e-posta veya parola.", "error");
      } else {
        window.NovaUi.showStatus(
          statusEl,
          (err && err.message) || "Giriş başarısız oldu.",
          "error"
        );
      }
      passwordInput.value = "";
      passwordInput.focus();
    } finally {
      submitBtn.disabled = false;
      submitBtn.textContent = "Giriş Yap";
    }
  });
})();
